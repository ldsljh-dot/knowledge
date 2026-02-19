수집된 RAG manifest를 기반으로 기존 자료에서 즉시 질문-답변합니다 (웹 검색 없음).

모든 bash 명령은 프로젝트 루트(`/home/jh/projects/knowledge`)에서 실행합니다.

---

## Phase 1: RAG Manifest 조회 및 토픽 선택

### Step 1-1: 기존 RAG 목록 확인

```bash
set -a && source .env && set +a
RAG_ROOT="$OBSIDIAN_VAULT_PATH/rag"

python3 -c "
import json, os, pathlib
rag_root = pathlib.Path('$RAG_ROOT')
if not rag_root.exists():
    print('RAG 디렉토리가 없습니다. knowledge_tutor로 먼저 수집하세요.')
    exit()
manifests = list(rag_root.glob('*/manifest.json'))
if not manifests:
    print('등록된 RAG가 없습니다. /knowledge_tutor를 먼저 실행하세요.')
else:
    for m in sorted(manifests):
        d = json.loads(m.read_text())
        print(f\"  - {d['topic']}  ({d['file_count']}파일, {d['total_bytes']//1024}KB, {d.get('updated','?')[:10]})\")
"
```

### Step 1-2: 사용자 토픽 선택

사용자에게 질문합니다:
> **"어떤 주제를 검색하시겠습니까?**
> 위 목록에서 토픽명을 입력하거나, `전체`로 모든 자료를 검색합니다."

| 입력 | 처리 |
|------|------|
| 목록의 토픽명 | 해당 manifest 로드 → Step 1-3 |
| 목록에 없는 새 주제 | Step 1-4 (자동 수집 흐름) |
| `전체` / `all` | 모든 manifest의 source_dirs 합산 |
| 복수 토픽 (쉼표 구분) | 해당 manifest들 병합 |

### Step 1-3: Manifest에서 소스 경로 로드

```bash
SAFE_TOPIC=$(echo "{선택한_토픽}" | tr ' /' '_')

python3 -c "
import json, pathlib
m = pathlib.Path('$RAG_ROOT/$SAFE_TOPIC/manifest.json')
if not m.exists():
    print(f'manifest 없음: {m}')
    exit(1)
d = json.loads(m.read_text())
print('SOURCE_DIRS=' + ','.join(d['source_dirs']))
print(f\"파일: {d['file_count']}개 ({d['total_bytes']//1024} KB)\")
"
```

소스 경로가 없으면 사용자에게 재수집 여부를 묻고 Step 1-4로 이동합니다.

### Step 1-4: RAG 없음 — 자동 수집 흐름

manifest가 없거나 소스가 손상된 경우, `knowledge_tutor` Phase 1을 실행합니다:

```bash
set -a && source .env && set +a
SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
OUTPUT_DIR="$OBSIDIAN_VAULT_PATH/sources/$SAFE_TOPIC"

# Tavily 검색
python .agent/skills/tavily-search/scripts/search_tavily.py \
  --query "{TOPIC}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 5 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300

# RAG manifest 생성
python .agent/skills/rag-retriever/scripts/create_manifest.py \
  --topic "{TOPIC}" \
  --sources-dir "$OUTPUT_DIR" \
  --rag-root "$RAG_ROOT"
```

수집 후 manifest를 로드하고 Phase 2로 진행합니다.

---

## Phase 2: RAG Q&A 루프

### Step 2-1: 질문 입력받기

사용자에게 질문합니다:
> **"어떤 내용이 궁금하신가요?"**

### Step 2-2: RAG 청크 검색 실행

단일 토픽:

```bash
python .agent/skills/rag-retriever/scripts/retrieve_chunks.py \
  --query "{QUESTION}" \
  --sources-dir "{SOURCE_DIR}" \
  --top-k 5 \
  --chunk-size 800 \
  --show-stats
```

복수 토픽 (전체 / 다중 선택):

```bash
for DIR in {SOURCE_DIR_1} {SOURCE_DIR_2}; do
  echo "=== [$DIR] ==="
  python .agent/skills/rag-retriever/scripts/retrieve_chunks.py \
    --query "{QUESTION}" \
    --sources-dir "$DIR" \
    --top-k 3 \
    --chunk-size 800
done
```

> top-k 가이드: 사실 확인 → 3 / 개념 설명 → 5 / 복합 질문 → 8

### Step 2-3: 청크 기반 답변 생성

1. **근거 기반**: 검색된 청크 내용을 인용하여 답변
2. **출처 명시**: `📄 출처: {파일명} (chunk #{n}, score={s})`
3. **범위 초과**: 청크에 관련 내용이 없으면 `"수집된 자료에 해당 내용이 없습니다."` + 다른 토픽 검색 제안
4. **한국어 + 기술 용어 병기**

### Step 2-4: 후속 안내

답변 후 항상 표시:
```
[계속]  다른 질문을 입력하세요.
[범위]  다른 토픽도 추가로 검색할까요?
[신규]  이 주제로 웹 검색(/knowledge_tutor)을 추가 실행할까요?
[종료]  'exit' 또는 '종료'
```

### Step 2-5: 종료 감지

`종료`, `exit`, `quit`, `그만`, `끝`, `done` → Phase 3으로 이동

---

## Phase 3: 세션 Q&A Obsidian 저장 (선택)

사용자에게 저장 여부를 묻고, `y`이면:

```bash
set -a && source .env && set +a

python .agent/skills/obsidian-integration/scripts/save_to_obsidian.py \
  --topic "{검색_주제}_조회" \
  --content "{Q&A_기록}" \
  --summary "{핵심_포인트}" \
  --category "Knowledge_Query" \
  --vault-path "$OBSIDIAN_VAULT_PATH"
```
