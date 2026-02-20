AI Tutor workflow: Tavily 웹 검색 → BM25 RAG 튜터링 → Obsidian 저장

다음 단계를 순서대로 실행하세요. 모든 bash 명령은 프로젝트 루트(`/home/jh/projects/knowledge`)에서 실행합니다.
환경변수는 `.env`에서 자동으로 로드됩니다.

---

## Phase 1: 정보 수집

### Step 1-1: 환경변수 확인

```bash
set -a && source .env && set +a
echo "TAVILY_API_KEY: ${TAVILY_API_KEY:0:8}..."
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"
```

`TAVILY_API_KEY`가 없으면 사용자에게 `.env` 설정을 안내하고 중단합니다.

### Step 1-2: 학습 주제 입력받기

사용자에게 질문합니다:
> **"어떤 주제를 학습하시겠습니까?"**

사용자의 답변을 `TOPIC` 변수에 저장합니다.

### Step 1-3: Tavily 검색 실행

```bash
set -a && source .env && set +a
SAFE_TOPIC=$(echo "$TOPIC" | tr ' /' '_')
OUTPUT_DIR="$OBSIDIAN_VAULT_PATH/sources/$SAFE_TOPIC"

python .agent/skills/tavily-search/scripts/search_tavily.py \
  --query "$TOPIC" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 5 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300
```

> 💡 기술 주제는 `--include-domains "arxiv.org,nvidia.com,huggingface.co"` 추가 권장

### Step 1-4: 검색 결과 확인

```bash
ls -lh "$OUTPUT_DIR"
```

생성된 파일 목록과 각 파일 제목을 사용자에게 보여줍니다.

### Step 1-5: 결과 품질 검증

수집된 파일의 제목/내용이 주제와 무관하거나 `relevance_score`가 대부분 0.05 미만이면:

```bash
# Garbage 폴더 삭제 후 재검색
rm -rf "$OUTPUT_DIR"

# 영문 기술 쿼리로 구체화하여 재검색
python .agent/skills/tavily-search/scripts/search_tavily.py \
  --query "{구체화된_영문_쿼리}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 5 \
  --search-depth advanced \
  --use-jina \
  --include-domains "arxiv.org,huggingface.co,medium.com" \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 500
```

### Step 1-6: RAG Manifest 생성

수집 완료 후 반드시 실행합니다:

```bash
set -a && source .env && set +a
RAG_ROOT="$OBSIDIAN_VAULT_PATH/rag"

python .agent/skills/rag-retriever/scripts/create_manifest.py \
  --topic "$TOPIC" \
  --sources-dir "$OUTPUT_DIR" \
  --rag-root "$RAG_ROOT"
```

생성 위치: `$OBSIDIAN_VAULT_PATH/rag/$SAFE_TOPIC/manifest.json`

---

## Phase 2: 대화형 튜터링

### Step 2-1: 학습 모드 진입 확인

사용자에게 질문합니다:
> **"수집한 정보를 기반으로 학습을 시작하시겠습니까?**
> 종료하려면 언제든 `종료` 또는 `exit`를 입력하세요."

### Step 2-2: 초기 컨텍스트 확보 (RAG)

```bash
python .agent/skills/rag-retriever/scripts/retrieve_chunks.py \
  --query "$TOPIC 핵심 개념 아키텍처 특징" \
  --sources-dir "$OUTPUT_DIR" \
  --top-k 7 \
  --chunk-size 800 \
  --show-stats
```

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

### Step 2-4: Interactive Tutoring 루프

수집된 청크를 내부 컨텍스트로 활용하며 다음 규칙을 따릅니다:

1. **Socratic Method**: 개념 설명 후 반드시 이해도 확인 질문 제시
2. **정확성 우선**: 수집 자료에 근거해 답변, 불확실하면 명시
3. **한국어 + 기술 용어 병기**: *"자동 미분(Automatic Differentiation)은..."*
4. **Q&A 기록**: 모든 대화를 Phase 3 저장을 위해 내부 기록
5. **신뢰도 항상 표시**: 모든 답변 하단에 📊 RAG 신뢰도 배지를 포함

**답변 형식:**

```
{답변 내용}

📄 출처: {파일명} (chunk #{n}, score={s:.3f})

---
📊 RAG 신뢰도: {배지} {신뢰도}%  ({검색된_청크_수}개 청크 참조, max_score={max_score:.3f})

🤔 {이해도 확인 질문}
```

> ⚠️ 신뢰도가 🟠 낮음(20~49%) 또는 🔴 매우 낮음(0~19%)이면 다음 메시지를 강조:
> **"⚡ 신뢰도가 낮습니다. '추가 검색해줘'라고 입력하면 웹에서 최신 자료를 수집합니다."**

사용자 질문마다 RAG 재검색:

```bash
python .agent/skills/rag-retriever/scripts/retrieve_chunks.py \
  --query "{사용자_질문}" \
  --sources-dir "$OUTPUT_DIR" \
  --top-k 5 \
  --chunk-size 800
```

### Step 2-5: 추가 크롤링 요청 처리

사용자가 다음 키워드를 입력하면 추가 웹 크롤링을 실행합니다:
- `추가 검색`, `더 찾아봐`, `크롤링해줘`, `웹 검색`, `자료 추가`, `검색 보강`, `search more`

**추가 크롤링 흐름:**

```bash
set -a && source .env && set +a

python .agent/skills/tavily-search/scripts/search_tavily.py \
  --query "{현재_질문_또는_TOPIC}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 3 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300

python .agent/skills/rag-retriever/scripts/create_manifest.py \
  --topic "$TOPIC" \
  --sources-dir "$OUTPUT_DIR" \
  --rag-root "$RAG_ROOT"
```

크롤링 완료 후:
1. 동일 질문으로 RAG 재검색 (Step 2-4 재실행)
2. 신뢰도 재계산 후 개선 여부 표시:
   ```
   🔄 자료 보강 완료: {추가된_파일_수}개 파일 추가됨
   신뢰도 변화: {이전_신뢰도}% → {새_신뢰도}%
   ```

### Step 2-6: 실시간 자동 추가 검색 (범위 초과 시)

사용자 질문이 수집 자료 범위를 벗어나거나 신뢰도가 자동으로 낮게 측정되면 (신뢰도 < 20%):

```bash
python .agent/skills/tavily-search/scripts/search_tavily.py \
  --query "{질문_키워드}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 3

python .agent/skills/rag-retriever/scripts/create_manifest.py \
  --topic "$TOPIC" \
  --sources-dir "$OUTPUT_DIR" \
  --rag-root "$RAG_ROOT"
```

### Step 2-7: 종료 감지

`종료`, `exit`, `quit`, `그만`, `끝`, `done` 입력 시 → Phase 3으로 이동

---

## Phase 3: 결과 저장

### Step 3-1: 핵심 요약 생성

튜터링 세션 전체를 바탕으로 핵심 포인트 3~7개를 bullet point로 정리합니다.

### Step 3-2: 통합 노트 저장

```bash
set -a && source .env && set +a
SOURCES=$(ls "$OUTPUT_DIR"/*.md 2>/dev/null | tr '\n' ',' | sed 's/,$//')

python .agent/skills/obsidian-integration/scripts/save_to_obsidian.py \
  --topic "$TOPIC" \
  --content "{학습_내용_및_QA_기록}" \
  --summary "{핵심_요약}" \
  --category "AI_Study" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --sources "$SOURCES"
```

### Step 3-3: 완료 메시지 출력

```
✅ 학습을 완료했습니다!

📁 생성된 파일:
  - 통합 노트: $OBSIDIAN_VAULT_PATH/{날짜}_{TOPIC}.md
  - 원본 자료: $OUTPUT_DIR/ (총 N개 파일)
  - RAG manifest: $RAG_ROOT/$SAFE_TOPIC/manifest.json

💡 다음에 이 주제를 다시 조회하려면:
   /knowledge_query → '$TOPIC' 선택
```
