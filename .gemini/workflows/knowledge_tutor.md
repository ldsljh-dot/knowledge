---
description: AI Tutor workflow - Tavily 웹 검색 + Socratic 튜터링 + Obsidian 저장 + RAG manifest 생성
trigger: /knowledge_tutor
---

# Knowledge Tutor Workflow

> 💡 **OS 실행 규칙**: 현재 시스템의 OS를 감지하여 적절한 셸을 사용하세요.
> - **Linux/macOS**: `bash`를 사용하여 실행합니다.
> - **Windows**: `powershell`을 사용하여 실행하며, 변수 및 명령어 구문을 Windows 환경에 맞게 조정합니다.

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

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드 및 AGENT_ROOT 설정
if [ -f .env ]; then set -a; source .env; set +a; fi
# .env에 AGENT_ROOT가 없다면 현재 디렉토리를 사용
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "AGENT_ROOT: $AGENT_ROOT"
echo "TAVILY_API_KEY: ${TAVILY_API_KEY:0:8}..."
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"

# 의존성 패키지 확인
if ! python -c "import tavily, rank_bm25" &> /dev/null; then
  echo "⚠️ 필수 패키지가 설치되지 않았습니다. 설치를 진행합니다..."
  pip install -r "$AGENT_ROOT/requirements.txt"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# .env 파일 로드
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}

# AGENT_ROOT 설정
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

Write-Host "AGENT_ROOT: $env:AGENT_ROOT"
if ($env:TAVILY_API_KEY) { Write-Host "TAVILY_API_KEY: $($env:TAVILY_API_KEY.Substring(0,8))..." }
Write-Host "OBSIDIAN_VAULT_PATH: $env:OBSIDIAN_VAULT_PATH"

# 의존성 패키지 확인
try {
    python -c "import tavily, rank_bm25" *>$null
} catch {
    Write-Host "⚠️ 필수 패키지가 설치되지 않았습니다. 설치를 진행합니다..."
    pip install -r "$env:AGENT_ROOT\requirements.txt"
}
```

</tab>
</tabs>

> ⚠️ `TAVILY_API_KEY`가 없으면 워크플로우를 진행할 수 없습니다.  
> `.env.example`을 복사해 `.env`를 설정하거나 환경변수를 직접 설정하세요.

---

## Phase 1: 정보 수집

### Step 1-1: 학습 주제 입력받기

사용자에게 두 가지를 질문합니다:

1. **"어떤 주제를 학습하시겠습니까?"**
   예: `PyTorch autograd 동작 원리`, `CXL memory pooling`, `NVBit 메모리 추적`

2. **"어떤 카테고리에 분류하시겠습니까?"**
   예: `PyTorch`, `CUDA`, `NVBit`, `자율주행`, `반도체`
   (기존 카테고리 확인: `{OBSIDIAN_VAULT_PATH}/Agent/` 폴더 목록 참고)

사용자의 답변을 `{TOPIC}`과 `{CATEGORY}` 변수에 저장합니다.

---

### Step 1-2: SKILL 문서 확인 (필수)

검색을 실행하기 전에 반드시 skill 문서를 읽으세요:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi
cat "$AGENT_ROOT/.gemini/skills/tavily-search/SKILL.md"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }
Get-Content "$env:AGENT_ROOT/.gemini/skills/tavily-search/SKILL.md"
```

</tab>
</tabs>

---

### Step 1-3: Tavily 검색 실행

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
OUTPUT_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

# 검색 실행
python "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
  --query "{TOPIC}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 5 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300

if [ $? -ne 0 ]; then
  echo "❌ 검색 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# .env 로드
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"
$OUTPUT_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

# 검색 실행
python "$env:AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" `
  --query "{TOPIC}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 5 `
  --search-depth advanced `
  --use-jina `
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" `
  --min-content-length 300

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 검색 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

> 💡 특정 기술 주제는 `--include-domains "nvidia.com,arxiv.org,docs.nvidia.com"` 추가 권장

---

### Step 1-4: 검색 결과 확인

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
ls -lh "$OUTPUT_DIR"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
Get-ChildItem -Path "$OUTPUT_DIR" | Select-Object Name, Length, LastWriteTime
```

</tab>
</tabs>

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

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
rm -rf "$OUTPUT_DIR"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
Remove-Item -Recurse -Force "$OUTPUT_DIR"
```

</tab>
</tabs>

2. **쿼리 구체화 후 재검색**

모호한 단어는 영어 + 기술 맥락을 명확히 지정합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 예시: "mamba 기술적 의미" → "Mamba SSM architecture deep learning"
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{REFINED_TOPIC}" | tr ' /' '_')
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
OUTPUT_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

python "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
  --query "{REFINED_TOPIC}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 5 \
  --search-depth advanced \
  --use-jina \
  --include-domains "arxiv.org,huggingface.co,medium.com" \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 500

if [ $? -ne 0 ]; then
  echo "❌ 재검색 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_TOPIC = "{REFINED_TOPIC}" -replace '[ /]', '_'
$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"
$OUTPUT_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

python "$env:AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" `
  --query "{REFINED_TOPIC}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 5 `
  --search-depth advanced `
  --use-jina `
  --include-domains "arxiv.org,huggingface.co,medium.com" `
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" `
  --min-content-length 500

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 재검색 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

> 💡 **쿼리 구체화 팁:**
> - 한국어 혼용 대신 **영문 기술 쿼리** 사용
> - 모호한 용어는 도메인 키워드를 명시 (예: `deep learning`, `architecture`)
> - `--include-domains`로 신뢰 소스를 한정

3. **재검색 결과를 다시 Step 1-4로 돌아가 확인**

---

### Step 1-6: RAG Manifest 생성 ⭐

수집이 완료되면 **반드시** RAG manifest를 생성합니다.
이 manifest는 `/knowledge_query` 워크플로우에서 RAG 검색 시 사용됩니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
SOURCES_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
RAG_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "{TOPIC}" \
  --sources-dir "$SOURCES_DIR" \
  --output-dir "$RAG_DIR" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --category "{CATEGORY}"

if [ $? -ne 0 ]; then
  echo "❌ Manifest 생성 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# .env 로드
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"
$SOURCES_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
$RAG_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$SOURCES_DIR" `
  --output-dir "$RAG_DIR" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --category "{CATEGORY}"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Manifest 생성 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

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

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
  --query "{TOPIC} 핵심 개념 아키텍처 특징" \
  --sources-dir "$OUTPUT_DIR" \
  --top-k 7 \
  --chunk-size 1200 \
  --show-stats

if [ $? -ne 0 ]; then
  echo "❌ RAG 초기 컨텍스트 확보 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" `
  --query "{TOPIC} 핵심 개념 아키텍처 특징" `
  --sources-dir "$OUTPUT_DIR" `
  --top-k 7 `
  --chunk-size 1200 `
  --show-stats

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ RAG 초기 컨텍스트 확보 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

#### Step 2-2-b: 사용자 질문마다 재검색

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
  --query "{USER_QUESTION}" \
  --sources-dir "$OUTPUT_DIR" \
  --top-k 5 \
  --chunk-size 1200

if [ $? -ne 0 ]; then
  echo "❌ 질문 관련 RAG 검색 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" `
  --query "{USER_QUESTION}" `
  --sources-dir "$OUTPUT_DIR" `
  --top-k 5 `
  --chunk-size 1200

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 질문 관련 RAG 검색 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

> 💡 **전략**: 질문이 바뀔 때마다 재검색 → 항상 현재 질문과 가장 관련된 청크만 컨텍스트에 올라감

---

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

---

### Step 2-4: Interactive Tutoring 루프

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

5. **신뢰도 항상 표시**
   - 모든 답변 하단에 📊 RAG 신뢰도 배지를 포함

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

---

### Step 2-5: 추가 크롤링 요청 처리

사용자가 다음 키워드를 입력하면 추가 웹 크롤링을 실행합니다:
- `추가 검색`, `더 찾아봐`, `크롤링해줘`, `웹 검색`, `자료 추가`, `검색 보강`, `search more`

**추가 크롤링 흐름:**

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
OUTPUT_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
RAG_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
  --query "{현재_질문_또는_TOPIC}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 3 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "{TOPIC}" \
  --sources-dir "$OUTPUT_DIR" \
  --output-dir "$RAG_DIR" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --category "{CATEGORY}"

if [ $? -ne 0 ]; then
  echo "❌ 추가 크롤링 후 Manifest 업데이트 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"
$OUTPUT_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
$RAG_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$env:AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" `
  --query "{현재_질문_또는_TOPIC}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 3 `
  --search-depth advanced `
  --use-jina `
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" `
  --min-content-length 300

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$OUTPUT_DIR" `
  --output-dir "$RAG_DIR" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --category "{CATEGORY}"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 추가 크롤링 후 Manifest 업데이트 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

크롤링 완료 후:
1. 동일 질문으로 RAG 재검색 (Step 2-4 재실행)
2. 신뢰도 재계산 후 개선 여부 표시:
   ```
   🔄 자료 보강 완료: {추가된_파일_수}개 파일 추가됨
   신뢰도 변화: {이전_신뢰도}% → {새_신뢰도}%
   ```

---

### Step 2-6: 실시간 자동 추가 검색 (범위 초과 시)

사용자 질문이 수집된 자료 범위를 벗어나거나 신뢰도가 자동으로 낮게 측정되면 (신뢰도 < 20%):

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
OUTPUT_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
RAG_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
  --query "{사용자_질문_키워드}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 3

# 추가 수집 후 manifest도 업데이트
python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "{TOPIC}" \
  --sources-dir "$OUTPUT_DIR" \
  --output-dir "$RAG_DIR" \
  --vault-path "$OBSIDIAN_VAULT_PATH"

if [ $? -ne 0 ]; then
  echo "❌ 수집 후 Manifest 업데이트 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"
$OUTPUT_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
$RAG_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$env:AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" `
  --query "{사용자_질문_키워드}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 3

# 추가 수집 후 manifest도 업데이트
python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$OUTPUT_DIR" `
  --output-dir "$RAG_DIR" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 수집 후 Manifest 업데이트 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

---

### Step 2-7: 종료 감지

사용자가 다음 중 하나를 입력하면 Phase 3으로 이동:
- `종료`, `exit`, `quit`, `그만`, `끝`, `done`

---

## Phase 3: 결과 저장

### Step 3-1: 전체 대화 내역 및 핵심 요약 정리

1. **전체 대화 기록(QA_HISTORY)**: Phase 2에서 진행된 모든 질문(User)과 답변(Assistant)을 생략 없이 텍스트로 누적합니다.
2. **핵심 요약(SUMMARY)**: 전체 세션을 바탕으로 핵심 포인트 3~7개를 bullet point로 정리합니다.

### Step 3-2: 통합 노트 저장 (전체 내역 포함) ⭐

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
OUTPUT_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

# 소스 파일 목록 생성 (쉼표로 구분)
SOURCES=$(ls "$OUTPUT_DIR"/*.md 2>/dev/null | tr '\n' ',' | sed 's/,$//')

# --append 플래그: 동일 주제 파일이 있으면 세션 블록 누적 추가, 없으면 새로 생성
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{TOPIC}" \
  --content "{전체_대화_기록_QA_HISTORY}" \
  --summary "{핵심_요약_SUMMARY}" \
  --category "AI_Study" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY" \
  --sources "$SOURCES" \
  --append

if [ $? -ne 0 ]; then
  echo "❌ Obsidian 노트 저장 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"
$OUTPUT_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

# 소스 파일 목록 생성 (쉼표로 구분)
$SOURCES_LIST = Get-ChildItem -Path "$OUTPUT_DIR/*.md" | Select-Object -ExpandProperty FullName
$SOURCES = $SOURCES_LIST -join ","

# --append 플래그: 동일 주제 파일이 있으면 세션 블록 누적 추가, 없으면 새로 생성
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}" `
  --content "{전체_대화_기록_QA_HISTORY}" `
  --summary "{핵심_요약_SUMMARY}" `
  --category "AI_Study" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY" `
  --sources "$SOURCES" `
  --append

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Obsidian 노트 저장 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

> 💡 **중요**: `{전체_대화_기록_QA_HISTORY}`에는 사용자와의 모든 대화 내용이 포함되어야 합니다. 요약본이 아닌 실제 대화 로그를 저장하세요.

### Step 3-3: 대시보드 업데이트

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"

python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" \
  --agent-dir "$AGENT_DIR" \
  --output "$AGENT_DIR/_Dashboard.md"

if [ $? -ne 0 ]; then
  echo "❌ 대시보드 업데이트 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" `
  --agent-dir "$AGENT_DIR" `
  --output "$AGENT_DIR/_Dashboard.md"
```

</tab>
</tabs>

### Step 3-4: 완료 메시지

```
✅ 학습을 완료했습니다!

📁 생성/업데이트된 파일:
  - 누적 노트: Agent/{CATEGORY}/{TOPIC}.md  ← 세션이 쌓일수록 기록이 누적됩니다
  - 원본 자료: Agent/{CATEGORY}/sources/{safe_topic}/ (총 N개 파일)
  - RAG manifest: Agent/{CATEGORY}/rag/{safe_topic}/manifest.json
  - 대시보드: Agent/_Dashboard.md (업데이트됨)

💡 같은 주제로 다음 세션을 진행하면 동일 노트에 '세션 2', '세션 3'... 이 추가됩니다.
💡 다음에 이 주제를 다시 조회하려면:
   /knowledge_query → '{CATEGORY}/{safe_topic}' 선택

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
