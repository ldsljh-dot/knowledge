---
description: AI Tutor workflow - Tavily 웹 검색 + Socratic 튜터링 + Obsidian 저장 + RAG manifest 생성
trigger: /knowledge_tutor
---

# Knowledge Tutor Workflow

사용자가 학습하고 싶은 주제를 입력하면:
1. Tavily 웹 검색으로 최신 자료 수집
2. **RAG manifest 생성** (`/rag/{topic}/manifest.json`)
3. 수집된 자료를 기반으로 Socratic Method 대화형 튜터링
4. 학습 내용을 Obsidian 노트로 저장

수집 후에는 `/knowledge_query` 워크플로우에서 RAG manifest를 사용해
웹 검색 없이 즉시 질문-답변을 할 수 있습니다.

---

## Prerequisites

실행 전 다음을 확인하세요:

```powershell
echo "TAVILY_API_KEY: $($env:TAVILY_API_KEY.Substring(0,8))..."
echo "OBSIDIAN_VAULT_PATH: $env:OBSIDIAN_VAULT_PATH"
```

> ⚠️ `TAVILY_API_KEY`가 없으면 워크플로우를 진행할 수 없습니다.  
> `.env.example`을 복사해 `.env`를 설정하거나 환경변수를 직접 설정하세요.

---

## Phase 1: 정보 수집

### Step 1-1: 학습 주제 입력받기

사용자에게 질문합니다:

> **"어떤 주제를 학습하시겠습니까?"**  
> 예: `PyTorch autograd 동작 원리`, `CXL memory pooling`, `NAND FTL 알고리즘`

사용자의 답변을 `{TOPIC}` 변수에 저장합니다.

---

### Step 1-2: SKILL 문서 확인 (필수)

검색을 실행하기 전에 반드시 skill 문서를 읽으세요:

```powershell
Get-Content "$AGENT_ROOT\.agent\skills\tavily-search\SKILL.md"
```

---

### Step 1-3: Tavily 검색 실행

```powershell
$AGENT_ROOT = "C:\Users\ldslj\OneDrive\문서\work\claude\knowledge_collector"
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]','_'
$OUTPUT_DIR = "$env:OBSIDIAN_VAULT_PATH\sources\$SAFE_TOPIC"

python "$AGENT_ROOT\.agent\skills\tavily-search\scripts\search_tavily.py" `
  --query "{TOPIC}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 5 `
  --search-depth advanced `
  --use-jina `
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" `
  --min-content-length 300
```

> 💡 특정 기술 주제는 `--include-domains "nvidia.com,arxiv.org,docs.nvidia.com"` 추가 권장

---

### Step 1-4: 검색 결과 확인

```powershell
Get-ChildItem "$OUTPUT_DIR" | Select-Object Name, Length | Format-Table
```

생성된 파일 목록과 각 파일의 제목(title frontmatter)을 사용자에게 제시합니다.

---

### Step 1-5: 결과 품질 검증 및 Garbage 정리 ⚠️

**검색 결과가 주제와 무관하다고 판단될 경우**, 아래 절차를 수행합니다.

#### 품질 기준 (이 중 하나라도 해당하면 재검색 필요)
- 수집된 파일의 `relevance_score`가 대부분 0.05 미만
- 파일 제목 또는 내용에 주제와 무관한 키워드가 다수 등장 (예: 주식, 쇼핑, 광고 등)
- Tavily AI Summary가 주제와 전혀 관련 없는 내용을 요약하고 있음

#### 처리 절차

1. **Garbage 폴더 삭제**

```powershell
Remove-Item -Recurse -Force "$OUTPUT_DIR"
```

2. **쿼리 구체화 후 재검색**

모호한 단어는 영어 + 기술 맥락을 명확히 지정합니다.

```powershell
# 예시: "mamba 기술적 의미" → "Mamba SSM architecture deep learning"
$SAFE_TOPIC = "{REFINED_TOPIC}" -replace '[ /]','_'
$OUTPUT_DIR = "$env:OBSIDIAN_VAULT_PATH\sources\$SAFE_TOPIC"

python "$AGENT_ROOT\.agent\skills\tavily-search\scripts\search_tavily.py" `
  --query "{REFINED_TOPIC}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 5 `
  --search-depth advanced `
  --use-jina `
  --include-domains "arxiv.org,huggingface.co,medium.com" `
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" `
  --min-content-length 500
```

> 💡 **쿼리 구체화 팁:**
> - 한국어 혼용 대신 **영문 기술 쿼리** 사용
> - 모호한 용어는 도메인 키워드를 명시 (예: `deep learning`, `architecture`)
> - `--include-domains`로 신뢰 소스를 한정

3. **재검색 결과를 다시 Step 1-4로 돌아가 확인**

---

### Step 1-6: RAG Manifest 생성 ⭐

수집이 완료되면 **반드시** RAG manifest를 생성합니다.
이 manifest는 `/knowledge_query` 워크플로우에서 RAG 검색 시 사용됩니다.

```powershell
$RAG_ROOT = "$env:OBSIDIAN_VAULT_PATH\rag"

python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$OUTPUT_DIR" `
  --rag-root "$RAG_ROOT"
```

> 📁 생성 위치: `{OBSIDIAN_VAULT_PATH}/rag/{safe_topic}/manifest.json`
>
> manifest에는 다음 정보가 저장됩니다:
> - 토픽명 (`topic`, `safe_topic`)
> - 소스 파일 디렉토리 경로 (`source_dirs`)
> - 수집된 파일 목록 및 크기 (`files`, `file_count`, `total_bytes`)
> - 생성/업데이트 시각 (`created`, `updated`)

---

## Phase 2: 대화형 튜터링

### Step 2-1: 학습 모드 진입 확인

사용자에게 질문합니다:

> **"수집한 정보를 기반으로 학습을 시작하시겠습니까?**  
> 종료하려면 언제든 `종료` 또는 `exit`를 입력하세요."

---

### Step 2-2: 수집된 자료 읽기 (RAG)

전체 파일을 통째로 읽는 대신, **RAG Retriever로 질문과 관련된 청크만** 추출합니다.

#### Step 2-2-a: 튜터링 시작 시 초기 컨텍스트 확보

```powershell
python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\retrieve_chunks.py" `
  --query "{TOPIC} 핵심 개념 아키텍처 특징" `
  --sources-dir "$OUTPUT_DIR" `
  --top-k 7 `
  --chunk-size 800 `
  --show-stats
```

#### Step 2-2-b: 사용자 질문마다 재검색

```powershell
python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\retrieve_chunks.py" `
  --query "{USER_QUESTION}" `
  --sources-dir "$OUTPUT_DIR" `
  --top-k 5 `
  --chunk-size 800
```

> 💡 **전략**: 질문이 바뀔 때마다 재검색 → 항상 현재 질문과 가장 관련된 청크만 컨텍스트에 올라감

---

### Step 2-3: Interactive Tutoring 루프

수집된 자료를 **내부 컨텍스트**로 활용하며 다음 규칙으로 튜터링합니다:

#### 튜터링 규칙

1. **Socratic Method 적용**
   - 개념 설명 후 반드시 이해도 확인 질문 제시

2. **정확성 우선**
   - 수집된 자료에 근거해 답변
   - 불확실한 내용은 "추가 검색이 필요합니다"라고 명시

3. **한국어 응답 + 기술 용어 병기**
   - 예: *"자동 미분(Automatic Differentiation)은..."*

4. **학습 대화 기록**
   - 모든 Q&A를 내부적으로 기록 → Phase 3에서 노트에 포함

---

### Step 2-4: 실시간 추가 검색

사용자 질문이 수집된 자료 범위를 벗어날 경우:

```powershell
python "$AGENT_ROOT\.agent\skills\tavily-search\scripts\search_tavily.py" `
  --query "{사용자_질문_키워드}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 3

# 추가 수집 후 manifest도 업데이트
python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$OUTPUT_DIR" `
  --rag-root "$RAG_ROOT"
```

---

### Step 2-5: 종료 감지

사용자가 다음 중 하나를 입력하면 Phase 3으로 이동:
- `종료`, `exit`, `quit`, `그만`, `끝`, `done`

---

## Phase 3: 결과 저장

### Step 3-1: 핵심 요약 생성

튜터링 세션 전체를 바탕으로 핵심 포인트 3~7개를 bullet point로 정리합니다.

### Step 3-2: 통합 노트 저장

```powershell
$SOURCES = (Get-ChildItem "$OUTPUT_DIR\*.md" | ForEach-Object { $_.FullName }) -join ","

python "$AGENT_ROOT\.agent\skills\obsidian-integration\scripts\save_to_obsidian.py" `
  --topic "{TOPIC}" `
  --content "{학습_내용_및_QA_기록}" `
  --summary "{핵심_요약}" `
  --category "AI_Study" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --sources "$SOURCES"
```

### Step 3-3: 완료 메시지

```
✅ 학습을 완료했습니다!

📁 생성된 파일:
  - 통합 노트: {OBSIDIAN_VAULT_PATH}/{날짜}_{TOPIC}.md
  - 원본 자료: {OUTPUT_DIR}/ (총 N개 파일)
  - RAG manifest: {OBSIDIAN_VAULT_PATH}/rag/{safe_topic}/manifest.json

💡 다음에 이 주제를 다시 조회하려면:
   /knowledge_query → '{TOPIC}' 선택

Obsidian에서 확인해보세요! 🎉
```

---

## Notes

- **RAG manifest**: Step 1-6에서 생성, `/knowledge_query` 워크플로우와 연동
- **Garbage 방지**: Step 1-5에서 품질 검증 후 불합격 시 폴더 삭제 및 재검색
- **RAG 전략**: Full text는 Obsidian에 보존, 튜터링 시에는 BM25 청크 검색으로 토큰 절감 (~94%)
- **의존성**:
  - `tavily-python` — 웹 검색
  - `rank-bm25` — RAG 청크 검색
  - `pdfplumber` — PDF 직접 파싱
  - `python-dotenv` — 환경변수 로드 (선택)
  - Jina Reader (`r.jina.ai`) — 전체 페이지 수집
