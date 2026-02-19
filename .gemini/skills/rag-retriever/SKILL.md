---
name: rag-retriever
description: "수집된 .md 소스 파일을 BM25로 청크 검색하여 LLM 컨텍스트 토큰을 절감하는 스킬입니다. Full text는 Obsidian에 그대로 보존하고, 질문과 관련된 청크만 추출하여 LLM에 전달합니다."
---

# RAG Retriever Skill

BM25(Okapi BM25) 기반 청크 검색 스킬입니다.
수집된 `.md` 파일을 **Obsidian에 그대로 보존**하면서, LLM 튜터링 시에는
질문과 관련된 청크만 추출해 컨텍스트 토큰을 대폭 절감합니다.

## 동작 구조

```
[저장된 .md 파일들]  ← Full text 보존 (Obsidian용)
        │
        ▼
  청크 분할 (chunk_size 단위, overlap으로 문맥 연결)
        │
        ▼
  BM25 유사도 계산 (쿼리 ↔ 각 청크)
        │
        ▼
  Top-K 청크만 stdout 출력  ← LLM 컨텍스트로 사용
```

## 사용법

```bash
cd <project_root>/.agent/skills/rag-retriever

python scripts/retrieve_chunks.py \
  --query "MIG 파티셔닝 원리" \
  --sources-dir "/path/to/vault/sources/nvidia_gpu_h100" \
  --top-k 5 \
  --chunk-size 800

# 토큰 절감 통계도 함께 확인
python scripts/retrieve_chunks.py \
  --query "Transformer Engine FP8 동작 방식" \
  --sources-dir "/path/to/vault/sources/nvidia_gpu_h100" \
  --top-k 5 \
  --show-stats
```

## 파라미터

| 파라미터 | 필수 | 기본값 | 설명 |
|----------|------|--------|------|
| `--query` | ✅ | — | 검색 쿼리 (사용자 질문 그대로 사용 가능) |
| `--sources-dir` | ✅ | — | 수집된 .md 파일 디렉토리 |
| `--top-k` | ❌ | `5` | 반환할 청크 수 |
| `--chunk-size` | ❌ | `800` | 청크 크기 (자) |
| `--overlap` | ❌ | `100` | 청크 간 겹침 크기 (문맥 연속성) |
| `--no-summary` | ❌ | `False` | summary 파일 제외 |
| `--glob` | ❌ | `*.md` | 읽을 파일 패턴 |
| `--show-stats` | ❌ | `False` | 토큰 절감 통계 stderr 출력 |

## 출력 형식

```markdown
# RAG Context — Query: "MIG 파티셔닝 원리"
# (전체 312개 청크 중 상위 5개 / top_k=5)

## [AI Summary]
...Tavily 요약 내용...

## [Related Chunks]

### [1] nvidia_H100_..._1_2026-02-19.md (chunk #14, score=8.421)
...관련 청크 텍스트...

### [2] nvidia_H100_..._2_2026-02-19.md (chunk #7, score=6.103)
...
```

## 토큰 절감 효과 (H100 예시)

| 방식 | 토큰 수 | 비고 |
|------|---------|------|
| 전체 파일 cat (기존) | ~80,000 | v2 Jina 수집 기준 |
| RAG top-k=5 (개선) | ~3,000~5,000 | 청크 크기에 따라 다름 |
| **절감률** | **~94%** | |

## 의존성

```
rank-bm25    # pip install rank-bm25
```

## 튜터링 워크플로우 연동

`knowledge_tutor.md` Step 2-2에서 전체 파일 읽기 대신 이 스킬을 사용합니다:

```bash
# 기존 (전체 파일 cat)
for f in "$OUTPUT_DIR"/*.md; do cat "$f"; done

# 개선 (RAG 청크 검색)
python retrieve_chunks.py \
  --query "{사용자_질문}" \
  --sources-dir "$OUTPUT_DIR" \
  --top-k 5 \
  --show-stats
```

사용자 질문이 바뀔 때마다 새로운 청크를 검색하므로,
항상 질문과 가장 관련 있는 내용만 LLM에 전달됩니다.
