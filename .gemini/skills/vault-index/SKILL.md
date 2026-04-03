# Vault Index Skill

Obsidian vault의 토픽 폴더를 벡터 임베딩으로 인덱싱하여 의미적 유사도 검색을 제공합니다.

## 의존성
- `qdrant-client` — 로컬 벡터 DB (`~/.mem0/qdrant` 공유)
- `sentence-transformers` — 로컬 임베딩 모델 (all-MiniLM-L6-v2)
- `OBSIDIAN_VAULT_PATH` 환경변수

## 스크립트

### vault_index.py — 인덱스 빌드 (Incremental)

```bash
# 기본 실행 (변경된 폴더만)
python .gemini/skills/vault-index/scripts/vault_index.py

# 전체 재빌드
python .gemini/skills/vault-index/scripts/vault_index.py --full

# 대상 미리 확인 (실행 없음)
python .gemini/skills/vault-index/scripts/vault_index.py --dry-run
```

**인덱싱 대상:** `sources/` 또는 `rag/` 가 있는 leaf 폴더
**PARA 스캔 범위:** `1-Projects`, `2-Areas`, `3-Resources`

### vault_search.py — 의미 검색

```bash
# 기본 검색
python .gemini/skills/vault-index/scripts/vault_search.py \
  --query "장기기억 메모리 AI 에이전트"

# 결과 수 및 임계값 조정
python .gemini/skills/vault-index/scripts/vault_search.py \
  --query "LLM 추론 최적화" \
  --top-k 5 \
  --threshold 0.3

# PARA 범위 필터
python .gemini/skills/vault-index/scripts/vault_search.py \
  --query "컴파일러 최적화" \
  --para 2-Areas

# JSON 출력 (워크플로우 파이프라인용)
python .gemini/skills/vault-index/scripts/vault_search.py \
  --query "메모리 시스템" --json
```

## 인덱스 구조

| 필드 | 내용 |
|------|------|
| `path` | vault 기준 상대 경로 (예: `2-Areas/LLM/Memory/mem0`) |
| `topic` | 폴더명 |
| `category` | 상위 경로 (예: `2-Areas/LLM/Memory`) |
| `para` | PARA 루트 (`1-Projects` / `2-Areas` / `3-Resources`) |
| `indexed_at` | 마지막 인덱싱 시각 (Unix timestamp) |
| `mtime` | sources/ 최신 파일 수정 시각 |

## 통합 포인트

- `knowledge_tutor` Step 1-1: 주제 입력 후 유사 폴더 검색 → 배치 위치 추천
- `knowledge_tutor` Phase 3: 저장 완료 후 자동 재인덱싱
- `knowledge_query` Step 0: 관련 기존 지식 탐색
- `/vault_reindex`: 수동 인덱스 갱신 커맨드
