#!/usr/bin/env python3
"""
Tavily Search Skill (v2)
AI-optimized web search with two-stage pipeline:
  Stage 1: Tavily → URL discovery + snippet
  Stage 2: Jina Reader → full page extraction (optional, --use-jina)

Usage:
    python scripts/search_tavily.py --query "PyTorch autograd" --output-dir ./out
    python scripts/search_tavily.py --query "H100 architecture" --output-dir ./out --use-jina
    python scripts/search_tavily.py --queries "H100 FP8,H100 MIG,H100 NVLink" --output-dir ./out --use-jina
    python scripts/search_tavily.py --query "H100" --output-dir ./out --include-domains nvidia.com,arxiv.org
"""

import os
import sys
import argparse
import urllib.request
import urllib.error
import io
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# .env 지원 (python-dotenv가 있으면 자동 로드)
try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    for _parent in [_here.parent, _here.parent.parent.parent.parent]:
        _env = _parent / ".env"
        if _env.exists():
            load_dotenv(_env)
            break
except ImportError:
    pass


# ────────────────────────── 유틸 ──────────────────────────

def safe_filename(text: str) -> str:
    """텍스트를 안전한 파일명으로 변환 (영숫자 + 언더바)"""
    return "".join([c if c.isalnum() else "_" for c in text])


def fetch_jina(url: str, timeout: int = 20) -> Optional[str]:
    """
    Jina Reader (r.jina.ai)로 URL 전체 페이지를 Markdown으로 수집.
    - X-Timeout: Jina 서버에 최대 대기 시간을 지시 (Medium 등 JS 렌더링 사이트 대응)
    - X-No-Cache: 캐시된 불완전 응답 방지
    실패 시 None 반환 (Tavily 스니펫으로 fallback).
    """
    jina_url = f"https://r.jina.ai/{url}"
    # X-Timeout은 urllib timeout보다 5초 여유를 둠
    jina_server_timeout = max(timeout - 5, 10)
    req = urllib.request.Request(
        jina_url,
        headers={
            "User-Agent": "Mozilla/5.0 (knowledge-collector/2.0)",
            "Accept": "text/markdown, text/plain, */*",
            "X-Timeout": str(jina_server_timeout),   # Jina가 JS 렌더링을 기다리는 시간
            "X-No-Cache": "true",                    # 캐시 갱신 강제
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            # Jina 응답 앞에 붙는 메타 헤더 제거
            # (Title:, URL:, Published:, Warning:, Timestamp: 로 시작하는 줄)
            lines = raw.splitlines()
            content_start = 0
            for i, line in enumerate(lines):
                if line.startswith(("Title:", "URL:", "Published", "Warning:", "Timestamp:")):
                    content_start = i + 1
                elif i > 15:
                    break
            return "\n".join(lines[content_start:]).strip()
    except Exception:
        return None


def fetch_pdf_jina(url: str, timeout: int = 20) -> Optional[str]:
    """
    Jina Reader에 PDF 전용 헤더(X-Return-Format: markdown)를 붙여 시도.
    일반 fetch_jina보다 더 긴 timeout을 기본으로 사용.
    """
    jina_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(
        jina_url,
        headers={
            "User-Agent": "Mozilla/5.0 (knowledge-collector/2.0)",
            "Accept": "text/markdown, text/plain, */*",
            "X-Return-Format": "markdown",
            "X-No-Cache": "true",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            lines = raw.splitlines()
            content_start = 0
            for i, line in enumerate(lines):
                if line.startswith(("Title:", "URL:", "Published", "Warning:")):
                    content_start = i + 1
                elif i > 15:
                    break
            return "\n".join(lines[content_start:]).strip()
    except Exception:
        return None


def fetch_pdf_pdfplumber(url: str, timeout: int = 30) -> Optional[str]:
    """
    PDF URL을 직접 다운로드하여 pdfplumber로 텍스트 추출.
    pdfplumber가 없으면 None 반환 (자동 skip).
    """
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return None  # pip install pdfplumber 필요

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (knowledge-collector/2.0)",
                "Accept": "application/pdf,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            pdf_bytes = resp.read()

        pages_text: List[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())

        if not pages_text:
            return None
        return "\n\n".join(pages_text)
    except Exception:
        return None


def is_pdf_url(url: str) -> bool:
    """URL이 PDF를 가리키는지 간단히 판단"""
    url_lower = url.lower().split("?")[0]  # 쿼리스트링 제거 후 판단
    return url_lower.endswith(".pdf")


def fetch_content(url: str, use_jina: bool, timeout: int, min_length: int) -> Tuple[Optional[str], str]:
    """
    URL 유형에 따라 콘텐츠를 수집하는 통합 함수.
    PDF 여부에 따라 3단계 fallback을 수행합니다:
      PDF URL → (1) Jina PDF 헤더 → (2) pdfplumber 직접 다운로드 → (3) None
      일반 URL → (1) Jina 일반 수집 → (2) None

    Returns:
        (content, source_tag) 또는 (None, "") 또는 (None, "manual_needed")
        source_tag="manual_needed": 콘텐츠는 없지만 커스터마 원세옵는 url에 유효 콘텐츠 존재 가능성 (수동 복사 필요)
    """
    if is_pdf_url(url):
        # Stage 1: Jina PDF 헤더 시도
        print(f"    [PDF] Jina PDF 헤더로 시도: {url[:60]}...")
        content = fetch_pdf_jina(url, timeout=timeout + 5)
        if content and not is_noise(content, min_length):
            print(f"    [PDF] Jina OK ({len(content):,}자)")
            return content, "jina_pdf"
        else:
            reason = "응답 없음" if content is None else f"너무 짧음 ({len(content or '')}자)"
            print(f"    [PDF] Jina fallback → pdfplumber ({reason})")

        # Stage 2: pdfplumber 직접 다운로드
        content = fetch_pdf_pdfplumber(url, timeout=timeout + 15)
        if content and not is_noise(content, min_length):
            print(f"    [PDF] pdfplumber OK ({len(content):,}자)")
            return content, "pdfplumber"
        else:
            reason = "pdfplumber 미설치 또는 추출 실패" if content is None else f"너무 짧음 ({len(content or '')}자)"
            print(f"    [PDF] pdfplumber fallback → Tavily 스니펫 ({reason})")

        return None, "tavily_snippet"

    elif use_jina:
        # 일반 URL: Jina 수집
        content = fetch_jina(url, timeout=timeout)
        if content is None:
            print(f"           fallback → Tavily 스니펫 (응답 없음)")
            return None, "tavily_snippet"
        if is_noise(content, min_length):
            # 노이즈이지만 차단 페이지 패턴이 감지된 경우 → 수동 복사 안내
            lower = content.lower()
            if any(pat in lower for pat in _BLOCK_PAGE_PATTERNS):
                print(f"           ⚠️  차단/CAPTCHA 감지 → 수동 복사 필요")
                return None, "manual_needed"
            print(f"           fallback → Tavily 스니펫 (너무 짧음 {len(content)}자)")
            return None, "tavily_snippet"
        return content, "jina_enhanced"

    return None, "tavily_snippet"


# Cloudflare / Rate-limit 대기 페이지에서 나타나는 패턴
# (내용 길이가 min_length를 넘겨도 이 패턴이 있으면 노이즈로 처리)
_BLOCK_PAGE_PATTERNS = [
    "just a moment",          # Cloudflare 대기 페이지
    "enable javascript",       # JS 비활성 안내
    "access denied",          # 403 페이지
    "too many requests",      # 429 Rate limit
    "rate limit",
    "please wait",
    "checking your browser",  # Cloudflare bot 검사
    "ddos protection",
    "verify you are human",
    "security verification",  # Medium 등 보안 검증 페이지
    "performing security",    # Medium CAPTCHA 대기
    "verifies you are not a bot",
]


def is_noise(content: str, min_length: int) -> bool:
    """
    내용이 너무 짧거나, Cloudflare/Rate-limit 대기 페이지면 노이즈로 판단.
    - min_length 미달
    - 대기/차단 페이지 패턴 포함 (길이와 무관하게 필터)
    """
    stripped = content.strip()
    if len(stripped) < min_length:
        return True
    # 대기/차단 페이지 감지: 전체 텍스트가 짧고 패턴이 있는 경우
    # (전체 텍스트가 3,000자 미만일 때만 패턴 검사 — 긴 글에는 단어가 자연스럽게 포함될 수 있음)
    if len(stripped) < 3000:
        lower = stripped.lower()
        if any(pat in lower for pat in _BLOCK_PAGE_PATTERNS):
            return True
    return False


# ────────────────────────── 파일 저장 ──────────────────────────

def create_source_file(
    output_dir: Path,
    query: str,
    source: Dict[str, Any],
    index: int,
    full_content: Optional[str] = None,
    source_tag: str = "tavily_snippet",
) -> str:
    """검색 결과 하나를 개별 md 파일로 저장"""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    title = source.get("title", "Untitled")
    safe_name = safe_filename(title)
    
    # 제목이 없거나 특수문자로만 되어있으면 쿼리를 대신 사용
    if not safe_name.strip("_"):
        safe_name = safe_filename(query)
        
    # 파일명 길이 제한 (Windows 호환성 등)
    if len(safe_name) > 150:
        safe_name = safe_name[:150]

    filename = f"{safe_name}_{index}_{timestamp}.md"
    filepath = output_dir / filename

    # title = source.get("title", "Untitled") # 이미 위에서 가져옴
    url     = source.get("url",     "")
    snippet = source.get("content", "")
    score   = source.get("score",   "")

    # source_tag에 따라 섹션 제목 결정
    if full_content and source_tag == "pdfplumber":
        content_section = f"## Full Content (via pdfplumber)\n\n{full_content}"
    elif full_content and source_tag == "jina_pdf":
        content_section = f"## Full Content (via Jina PDF)\n\n{full_content}"
    elif full_content:
        content_section = f"## Full Content (via Jina Reader)\n\n{full_content}"
        source_tag = "jina_enhanced"
    elif source_tag == "manual_needed":
        content_section = (
            "## \u26a0\ufe0f Manual Copy Required\n\n"
            "> **\uc790\ub3d9 \uc218\uc9d1 \uc2e4\ud328 (CAPTCHA / \uc811\uadfc \ucc28\ub2e8)**\n>\n"
            f"> \uc544\ub798 \ub9c1\ud06c\ub97c \ube0c\ub77c\uc6b0\uc800\uc5d0\uc11c \uc5f4\uace0, \uc804\uccb4 \ub0b4\uc6a9\uc744 \ubcf5\uc0ac\ud558\uc5ec \uc774 \uc139\uc158 \uc544\ub798\uc5d0 \ubd99\uc5ec\ub123\uc5b4 \uc8fc\uc138\uc694.\n>\n"
            f"> \U0001f517 {url}\n\n"
            "---\n\n"
            "*(\uc790\ub3d9 \uc218\uc9d1\ub41c \uc2a4\ub2c8\ud3ab)*\n\n"
            f"{snippet}"
        )
    else:
        content_section = f"## Snippet (via Tavily)\n\n{snippet}"
        source_tag = "tavily_snippet"

    text = f"""---
created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
source_url: {url}
title: "{title}"
search_query: "{query}"
source_index: {index}
relevance_score: {score}
content_source: {source_tag}
category: web_research
tags: [web_research, auto_generated, {source_tag}]
---

# {title}

**Source**: [{title}]({url})

{content_section}
"""
    filepath.write_text(text, encoding="utf-8")
    return str(filepath)


def create_summary_file(output_dir: Path, query: str, answer: str) -> str:
    """Tavily AI 요약을 별도 파일로 저장"""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    safe_query = safe_filename(query)
    filename = f"{safe_query}_summary_{timestamp}.md"
    filepath = output_dir / filename

    text = f"""---
created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
search_query: "{query}"
category: web_research
type: summary
tags: [web_research, summary, auto_generated]
---

# Summary: {query}

> AI-Generated Summary by Tavily

{answer}
"""
    filepath.write_text(text, encoding="utf-8")
    return str(filepath)


# ────────────────────────── 핵심 로직 ──────────────────────────

def search_and_save(
    query: str,
    output_dir: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    use_jina: bool = False,
    min_content_length: int = 200,
    jina_timeout: int = 15,
) -> List[str]:
    """
    Tavily API로 검색하고 결과를 개별 md 파일로 저장.
    use_jina=True 시 Jina Reader로 전체 페이지를 추가 수집.

    Returns:
        생성된 파일 경로 목록
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "TAVILY_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "  export TAVILY_API_KEY='tvly-...'  또는  .env 파일을 확인하세요."
        )

    from tavily import TavilyClient

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    jina_label = " + Jina" if use_jina else ""
    print(f"[Tavily{jina_label}] 검색: '{query}'  (depth={search_depth}, max={max_results})")
    if include_domains:
        print(f"  도메인 필터: {include_domains}")

    # ── Stage 1: Tavily 검색 ──
    client = TavilyClient(api_key=api_key)
    kwargs: Dict[str, Any] = dict(
        query=query,
        search_depth=search_depth,
        max_results=max_results,
        include_answer=True,
    )
    if include_domains:
        kwargs["include_domains"] = include_domains
    if exclude_domains:
        kwargs["exclude_domains"] = exclude_domains

    response = client.search(**kwargs)

    created: List[str] = []
    skipped = 0

    # Tavily AI 요약 저장
    if response.get("answer"):
        path = create_summary_file(output_path, query, response["answer"])
        created.append(path)
        print(f"  [summary] {Path(path).name}")

    # 개별 소스 처리
    for idx, result in enumerate(response.get("results", []), start=1):
        url     = result.get("url", "")
        snippet = result.get("content", "")
        title   = result.get("title", "Untitled")

        full_content: Optional[str] = None

        # ── Stage 2: 콘텐츠 수집 (PDF 감지 → 3단계 fallback) ──
        detected_is_pdf = is_pdf_url(url) if url else False
        if url and (use_jina or detected_is_pdf):
            label = f"PDF {idx}" if detected_is_pdf else f"Jina {idx}"
            print(f"  [{label}] 수집 중: {url[:60]}...")
            full_content, source_tag = fetch_content(
                url, use_jina=use_jina, timeout=jina_timeout, min_length=min_content_length
            )
            # CAPTCHA / 차단 감지 시 사용자에게 수동 복사 안내
            if source_tag == "manual_needed":
                print()
                print(f"  \u250c{'─'*62}\u2510")
                print(f"  \u2502 \u26a0\ufe0f  \uc790\ub3d9 \uc218\uc9d1 \uc2e4\ud328 (CAPTCHA / \uc811\uadfc \ucc28\ub2e8)          \u2502")
                print(f"  \u2502 \uc544\ub798 URL\uc744 \ube0c\ub77c\uc6b0\uc800\ub85c \uc5f4\uace0 \uc804\uccb4 \ub0b4\uc6a9\uc744 \ubcf5\uc0ac\ud55c \ub4a4,     \u2502")
                print(f"  \u2502 \uc800\uc7a5\ub41c .md \ud30c\uc77c\uc758 Manual Copy \uc139\uc158\uc5d0 \ubd99\uc5ec\ub123\uc73c\uc138\uc694. \u2502")
                print(f"  \u251c{'─'*62}\u2524")
                print(f"  \u2502 \U0001f517 {url}")
                print(f"  \u2514{'─'*62}\u2518")
                print()
        else:
            source_tag = "tavily_snippet"

        # 스니펫도 min_content_length 미달이면 건너뜀
        if full_content is None and is_noise(snippet, min_content_length):
            print(f"  [skip {idx}] '{title[:40]}' — 내용 너무 짧음 ({len(snippet)}자)")
            skipped += 1
            continue

        path = create_source_file(output_path, query, result, idx, full_content, source_tag)
        created.append(path)
        print(f"  [saved {idx}] ({source_tag}) {Path(path).name}")

    print(f"\n  {len(created)}개 저장, {skipped}개 필터됨 → {output_path}")
    return created


# ────────────────────────── CLI ──────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tavily Search Skill v2 — Tavily + Jina Reader 2-stage pipeline"
    )
    # 쿼리: 단일 or 다중
    qgroup = parser.add_mutually_exclusive_group(required=True)
    qgroup.add_argument("--query",   help="단일 검색 쿼리")
    qgroup.add_argument("--queries", help="다중 쿼리 (쉼표 구분). 예: 'H100 FP8,H100 MIG'")

    parser.add_argument("--output-dir",          required=True, help="결과 저장 디렉토리")
    parser.add_argument("--max-results",          type=int, default=5)
    parser.add_argument("--search-depth",         choices=["basic", "advanced"], default="advanced")
    parser.add_argument("--include-domains",      help="허용 도메인 (쉼표 구분). 예: nvidia.com,arxiv.org")
    parser.add_argument("--exclude-domains",      help="제외 도메인 (쉼표 구분). 예: reddit.com,youtube.com")
    parser.add_argument("--use-jina",             action="store_true", help="Jina Reader로 전체 페이지 수집")
    parser.add_argument("--min-content-length",   type=int, default=200, help="최소 콘텐츠 길이 (기본 200자)")
    parser.add_argument("--jina-timeout",         type=int, default=15,  help="Jina 요청 타임아웃(초)")

    args = parser.parse_args()

    include_domains = [d.strip() for d in args.include_domains.split(",")] if args.include_domains else None
    exclude_domains = [d.strip() for d in args.exclude_domains.split(",")] if args.exclude_domains else None
    queries = [q.strip() for q in args.queries.split(",")] if args.queries else [args.query]

    all_files: List[str] = []
    for q in queries:
        try:
            files = search_and_save(
                query=q,
                output_dir=args.output_dir,
                max_results=args.max_results,
                search_depth=args.search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                use_jina=args.use_jina,
                min_content_length=args.min_content_length,
                jina_timeout=args.jina_timeout,
            )
            all_files.extend(files)
        except Exception as e:
            print(f"[ERROR] '{q}': {e}", file=sys.stderr)

    print(f"\n총 {len(all_files)}개 파일 생성 완료.")
    for f in all_files:
        print(f"  - {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
