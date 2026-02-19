#!/usr/bin/env python3
"""
RAG Retriever Skill
BM25 기반 청크 검색 스크립트.

수집된 .md 파일들을 청크로 분할하고, 쿼리와 관련성 높은 청크만 추출하여
LLM 컨텍스트 토큰 소모를 줄입니다. Full text는 Obsidian에 그대로 보존됩니다.

목차/네비게이션 링크 덩어리 청크는 자동으로 필터링합니다 (--max-link-ratio).

Usage:
    python scripts/retrieve_chunks.py \
      --query "MIG 파티셔닝 원리" \
      --sources-dir "./sources/h100" \
      --top-k 5 \
      --chunk-size 800

    # 목차 필터 강도 조절 (기본 0.03: 청크 100자당 링크 3개 이상이면 노이즈)
    python scripts/retrieve_chunks.py \
      --query "FP8 동작 방식" \
      --sources-dir "./sources/h100" \
      --max-link-ratio 0.02

Output:
    stdout으로 관련 청크를 출력 → LLM이 컨텍스트로 사용
"""

import sys
import re
import argparse
from pathlib import Path
from typing import List, Tuple


# ────────────────────────── 청크 분할 ──────────────────────────

def split_into_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    텍스트를 chunk_size 단위로 분할. overlap으로 문맥 연속성 보장.
    - 문단(빈 줄) 경계를 우선 존중
    - 불가피할 경우 문자 단위로 자름
    """
    # frontmatter 제거 (--- ... --- 사이)
    text = re.sub(r'^---[\s\S]*?---\n', '', text, count=1).strip()

    paragraphs = re.split(r'\n{2,}', text)

    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # 단락 자체가 chunk_size보다 크면 강제 분할
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    sub = para[i:i + chunk_size]
                    if sub.strip():
                        chunks.append(sub.strip())
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


def is_toc_chunk(chunk: str, max_link_ratio: float, min_text_length: int = 80) -> bool:
    """
    목차/네비게이션/URL 잔재 청크 판별.

    판별 기준 (하나라도 해당하면 필터):
    1. min_text_length: URL·링크 제거 후 순수 텍스트가 너무 짧음
       → 실질 내용 없는 URL 잔재 조각 제거
    2. link_ratio: 마크다운 링크([text](url)) 밀도가 높음
       → 100자당 링크 수가 max_link_ratio 초과
    3. text_ratio: 링크 제거 후 순수 텍스트 비율이 30% 미만
       → 링크가 청크 대부분을 차지하는 목차 블록
    """
    # 마크다운 링크 및 독립 URL 모두 수집
    md_links  = re.findall(r'\[.*?\]\(https?://[^)]+\)', chunk)
    raw_urls  = re.findall(r'(?<!\()\bhttps?://\S+', chunk)
    link_count = len(md_links) + len(raw_urls)
    chunk_len  = max(len(chunk), 1)

    # 링크·URL 제거 후 순수 텍스트
    text_only = re.sub(r'\[.*?\]\(https?://[^)]+\)', '', chunk)
    text_only = re.sub(r'https?://\S+', '', text_only)
    text_only = re.sub(r'\s+', ' ', text_only).strip()

    # 조건 1: 순수 텍스트가 너무 짧음 (URL 잔재 조각)
    if len(text_only) < min_text_length:
        return True

    # 조건 2: 링크 밀도 초과
    link_ratio = link_count / (chunk_len / 100)
    if link_ratio > max_link_ratio:
        return True

    # 조건 3: 링크가 내용 대부분을 차지
    text_ratio = len(text_only) / chunk_len
    if link_count > 2 and text_ratio < 0.30:
        return True

    return False


def load_sources(sources_dir: Path, glob: str) -> List[Tuple[str, str]]:
    """
    sources_dir 내 .md 파일을 읽어 (파일명, 내용) 리스트 반환.
    summary 파일은 별도로 항상 포함 (맥락 제공용).
    """
    docs = []
    for path in sorted(sources_dir.glob(glob)):
        try:
            content = path.read_text(encoding="utf-8")
            docs.append((path.name, content))
        except Exception:
            pass
    return docs


# ────────────────────────── BM25 검색 ──────────────────────────

def tokenize(text: str) -> List[str]:
    """
    간단한 토크나이저.
    - 소문자화
    - 영문: 단어 단위
    - 한글: 2-gram (형태소 분석기 없이 근사)
    """
    text = text.lower()
    tokens = re.findall(r'[a-z0-9]+', text)

    # 한글 2-gram
    korean = re.findall(r'[\uac00-\ud7a3]+', text)
    for word in korean:
        tokens += [word[i:i+2] for i in range(len(word) - 1)]
        tokens.append(word)  # 전체 단어도 포함

    return tokens


def bm25_search(
    query: str,
    chunks: List[Tuple[str, str, int]],  # (source_name, chunk_text, chunk_idx)
    top_k: int,
) -> List[Tuple[float, str, str, int]]:
    """
    BM25로 쿼리와 관련된 청크 top_k개 반환.
    Returns: [(score, source_name, chunk_text, chunk_idx), ...]
    """
    from rank_bm25 import BM25Okapi

    if not chunks:
        return []

    tokenized_corpus = [tokenize(c[1]) for c in chunks]
    tokenized_query  = tokenize(query)

    bm25   = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    ranked = sorted(
        zip(scores, [c[0] for c in chunks], [c[1] for c in chunks], [c[2] for c in chunks]),
        key=lambda x: x[0],
        reverse=True,
    )
    # 점수가 0인 청크는 제외
    return [(s, src, txt, idx) for s, src, txt, idx in ranked[:top_k] if s > 0]


# ────────────────────────── 출력 포맷 ──────────────────────────

def format_output(
    query: str,
    results: List[Tuple[float, str, str, int]],
    summary_text: str,
    total_chunks: int,
    top_k: int,
) -> str:
    """LLM이 읽기 좋은 형태로 결과 포맷"""
    lines = []
    lines.append(f"# RAG Context — Query: \"{query}\"")
    lines.append(f"# (전체 {total_chunks}개 청크 중 상위 {len(results)}개 / top_k={top_k})")
    lines.append("")

    if summary_text:
        lines.append("## [AI Summary]")
        lines.append(summary_text.strip())
        lines.append("")

    if not results:
        lines.append("※ 관련 청크를 찾지 못했습니다. 쿼리를 바꿔보세요.")
        return "\n".join(lines)

    lines.append("## [Related Chunks]")
    for rank, (score, source, text, chunk_idx) in enumerate(results, 1):
        lines.append(f"\n### [{rank}] {source} (chunk #{chunk_idx}, score={score:.3f})")
        lines.append(text)

    return "\n".join(lines)


# ────────────────────────── 메인 ──────────────────────────

def retrieve(
    query: str,
    sources_dir: str,
    top_k: int = 5,
    chunk_size: int = 800,
    overlap: int = 100,
    glob: str = "*.md",
    include_summary: bool = True,
    max_link_ratio: float = 0.03,
) -> str:
    """
    메인 검색 함수.

    Args:
        max_link_ratio: 목차 청크 필터 임계값 (100자당 링크 수, 기본 0.03)
                        낮출수록 필터가 강해짐. 0.0이면 필터 비활성화.

    Returns:
        LLM 컨텍스트용 문자열 (stdout 출력 또는 직접 사용)
    """
    src_path = Path(sources_dir)
    if not src_path.exists():
        raise FileNotFoundError(f"sources_dir 없음: {sources_dir}")

    docs = load_sources(src_path, glob)
    if not docs:
        raise ValueError(f"{sources_dir} 에 .md 파일이 없습니다.")

    # summary 파일 분리
    summary_text = ""
    content_docs = []
    for name, content in docs:
        if "summary" in name.lower() and include_summary:
            summary_text = re.sub(r'^---[\s\S]*?---\n', '', content, count=1).strip()
        else:
            content_docs.append((name, content))

    # 청크 생성 + 목차 필터링
    all_chunks: List[Tuple[str, str, int]] = []
    filtered_count = 0
    for name, content in content_docs:
        chunks = split_into_chunks(content, chunk_size, overlap)
        for idx, chunk in enumerate(chunks):
            if max_link_ratio > 0 and is_toc_chunk(chunk, max_link_ratio):
                filtered_count += 1
                continue
            all_chunks.append((name, chunk, idx))

    # BM25 검색
    results = bm25_search(query, all_chunks, top_k)

    output = format_output(
        query=query,
        results=results,
        summary_text=summary_text,
        total_chunks=len(all_chunks),
        top_k=top_k,
    )

    # 필터 통계를 헤더에 추가
    if filtered_count > 0:
        header_note = f"# (목차/링크 청크 {filtered_count}개 필터됨)\n"
        output = output.replace(
            f"# (전체 {len(all_chunks)}개 청크 중",
            f"# (목차 필터 후 {len(all_chunks)}개 청크 중",
        )
        output = header_note + output

    return output


# ────────────────────────── CLI ──────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="RAG Retriever — BM25 기반 청크 검색 (토큰 절감)"
    )
    parser.add_argument("--query",          required=True,      help="검색 쿼리 (사용자 질문)")
    parser.add_argument("--sources-dir",    required=True,      help="수집된 .md 파일 디렉토리")
    parser.add_argument("--top-k",          type=int, default=5,    help="반환할 청크 수 (기본 5)")
    parser.add_argument("--chunk-size",     type=int, default=800,  help="청크 크기 (기본 800자)")
    parser.add_argument("--overlap",        type=int, default=100,  help="청크 간 겹침 (기본 100자)")
    parser.add_argument("--no-summary",     action="store_true",    help="summary 파일 제외")
    parser.add_argument("--glob",           default="*.md",         help="파일 패턴 (기본 *.md)")
    parser.add_argument("--show-stats",     action="store_true",    help="토큰 절감 통계 출력")
    parser.add_argument("--max-link-ratio", type=float, default=0.03,
                        help="목차 청크 필터 임계값: 100자당 링크 수 (기본 0.03). 0.0이면 필터 비활성화")

    args = parser.parse_args()

    try:
        result = retrieve(
            query=args.query,
            sources_dir=args.sources_dir,
            top_k=args.top_k,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            glob=args.glob,
            include_summary=not args.no_summary,
            max_link_ratio=args.max_link_ratio,
        )

        sys.stdout.reconfigure(encoding="utf-8")
        print(result)

        if args.show_stats:
            # 전체 파일 크기 vs 반환된 청크 크기 비교
            src_path = Path(args.sources_dir)
            total_chars = sum(
                len(p.read_text(encoding="utf-8"))
                for p in src_path.glob(args.glob)
            )
            result_chars = len(result)
            print("\n" + "="*50, file=sys.stderr)
            print(f"[통계] 전체 소스: {total_chars:,}자 (~{total_chars//4:,} tokens)", file=sys.stderr)
            print(f"[통계] RAG 출력:  {result_chars:,}자 (~{result_chars//4:,} tokens)", file=sys.stderr)
            print(f"[통계] 절감률:    {(1 - result_chars/total_chars)*100:.1f}%", file=sys.stderr)
            print("="*50, file=sys.stderr)

        return 0

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
