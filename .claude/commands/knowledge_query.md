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

### Step 2-3: RAG 신뢰도 계산

retrieve_chunks 출력에서 `score=X.XXX` 값들을 파싱하여 신뢰도를 계산합니다.

**신뢰도 계산 공식:**

```
검색된 청크가 없으면: 신뢰도 = 0%

max_score = 검색된 청크 중 가장 높은 BM25 score
avg_score = 상위 3개 청크 점수의 평균 (청크가 적으면 전체 평균)

score_grade:
  max_score == 0         → 0%
  0 < max_score < 0.5    → max_score / 0.5 * 25          (0~25%)
  0.5 ≤ max_score < 2.0  → 25 + (max_score-0.5)/1.5 * 30 (25~55%)
  2.0 ≤ max_score < 4.0  → 55 + (max_score-2.0)/2.0 * 25 (55~80%)
  max_score ≥ 4.0        → min(95, 80 + (max_score-4.0)*5) (80~95%)

신뢰도 = int(score_grade)
```

**신뢰도 배지:**
| 신뢰도 | 배지 | 의미 |
|--------|------|------|
| 80~100% | 🟢 높음 | 자료에 충분한 근거 있음 |
| 50~79%  | 🟡 보통 | 부분적 근거, 보완 가능 |
| 20~49%  | 🟠 낮음 | 관련 자료 부족, 추가 검색 권장 |
| 0~19%   | 🔴 매우 낮음 | 자료 없음, 반드시 추가 검색 필요 |

### Step 2-4: 청크 기반 답변 생성

답변 형식:

```
{답변 내용}

📄 출처: {파일명} (chunk #{n}, score={s:.3f})
...

---
📊 RAG 신뢰도: {배지} {신뢰도}%  ({검색된_청크_수}개 청크 참조, max_score={max_score:.3f})
```

규칙:
1. **근거 기반**: 검색된 청크 내용을 인용하여 답변
2. **출처 명시**: `📄 출처: {파일명} (chunk #{n}, score={s})`
3. **범위 초과**: 청크에 관련 내용이 없으면 `"수집된 자료에 해당 내용이 없습니다."` + 다른 토픽 검색 제안
4. **한국어 + 기술 용어 병기**
5. **신뢰도 항상 표시**: 모든 답변 하단에 📊 RAG 신뢰도 배지를 포함

### Step 2-5: 후속 안내

답변 후 항상 표시:
```
[계속]    다른 질문을 입력하세요.
[범위]    다른 토픽도 추가로 검색할까요?
[보강]    신뢰도가 낮으면 → "추가 검색해줘" / "더 찾아봐" / "크롤링해줘" 로 웹 검색 실행
[종료]    'exit' 또는 '종료'
```

> ⚠️ 신뢰도가 🟠 낮음(20~49%) 또는 🔴 매우 낮음(0~19%)이면 다음 메시지를 강조 표시:
> **"⚡ 신뢰도가 낮습니다. '추가 검색해줘'라고 입력하면 웹에서 최신 자료를 수집합니다."**

### Step 2-6: 추가 크롤링 요청 처리

사용자가 다음 키워드를 입력하면 추가 웹 크롤링을 실행합니다:
- `추가 검색`, `더 찾아봐`, `크롤링해줘`, `웹 검색`, `자료 추가`, `검색 보강`, `search more`

**추가 크롤링 흐름:**

```bash
set -a && source .env && set +a

# 현재 질문 또는 토픽으로 추가 검색
python .agent/skills/tavily-search/scripts/search_tavily.py \
  --query "{현재_질문_또는_TOPIC}" \
  --output-dir "{OUTPUT_DIR}" \
  --max-results 3 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300

# manifest 재생성 (새 파일 포함)
python .agent/skills/rag-retriever/scripts/create_manifest.py \
  --topic "{TOPIC}" \
  --sources-dir "{OUTPUT_DIR}" \
  --rag-root "$RAG_ROOT"
```

크롤링 완료 후:
1. Step 2-2를 재실행하여 동일 질문으로 RAG 재검색
2. 신뢰도를 다시 계산하여 개선 여부를 사용자에게 표시:
   ```
   🔄 자료 보강 완료: {추가된_파일_수}개 파일 추가됨
   신뢰도 변화: {이전_신뢰도}% → {새_신뢰도}%
   ```
3. 개선된 신뢰도로 답변을 갱신

### Step 2-7: 종료 감지

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
