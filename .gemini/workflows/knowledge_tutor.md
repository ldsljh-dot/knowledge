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

## Step 0: 이전 세션 문맥 로드 (Mem0)

학습 주제를 입력받은 후, Mem0에서 관련 이전 세션 이력을 검색합니다.
`ANTHROPIC_API_KEY`가 없으면 이 단계를 건너뜁니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
  python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" \
    --query "{TOPIC}" \
    --limit 3
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — 이전 세션 로드 건너뜀"
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

if ($env:ANTHROPIC_API_KEY) {
    python "$env:AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" `
      --query "{TOPIC}" `
      --limit 3
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — 이전 세션 로드 건너뜀"
}
```

</tab>
</tabs>

결과가 있으면 사용자에게 안내합니다:
> **"이 주제로 이전에 학습한 기록이 있습니다. 이어서 진행하시겠습니까?"**

---

## Phase 1: 정보 수집

### Step 1-1: 학습 주제 입력받기

사용자에게 다음을 질문합니다:

**"어떤 주제를 학습하시겠습니까?"**
예: `PyTorch autograd 동작 원리`, `CXL memory pooling`, `NVBit 메모리 추적`

사용자의 답변을 `{TOPIC}` 변수에 저장합니다.
저장될 카테고리(`{CATEGORY}`) 변수는 고정값인 `Inbox`로 설정합니다.

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
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
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
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
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
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
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
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
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
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
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
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
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

### Step 2-4: Interactive Tutoring 루프 (심층 해석 및 지식 합성)

수집된 자료를 **내부 컨텍스트**로 활용하며 다음 규칙으로 튜터링을 진행합니다. 단순 문답이 아니라, 전문가가 논문 수준의 리포트를 작성하듯 **깊이 있는 해석과 통찰**을 제공해야 합니다.

#### 튜터링 핵심 규칙

1. **심층 해석 및 확장 (Detailed Synthesis)**
   - 사용자의 질문이나 단편적인 키워드를 표면적으로만 대답하지 마십시오.
   - 검색된 RAG 데이터를 바탕으로 그 이면의 아키텍처적, 수학적, 기술적 원리와 병목, 시사점 등을 상세히 구조화하여 설명합니다. (예: [원리 설명] - [구조적 특징] - [한계 및 해결책])
2. **Socratic Method 연계**
   - 방대하고 깊이 있는 지식을 전달한 후, 사용자가 제대로 이해했는지 또는 한 단계 더 깊은 사고를 유도하기 위한 날카로운 확인 질문을 마지막에 제시합니다.
3. **정확성과 출처 명시**
   - 수집된 자료에 근거해 학술적/기술적으로 정확하게 답변합니다.
   - 불확실한 내용은 "추가 검색이 필요합니다"라고 명시합니다.
4. **한국어 응답 + 기술 용어 병기**
   - 예: *"자기 수정형 타이탄(Self-Modifying Titans)은 연속체 메모리 시스템(Continuum Memory System)과 결합하여..."*
5. **학습 대화 기록 (실시간 저장)**
   - 모든 심층 답변과 분석 내용을 출력한 직후, Step 2-5 절차에 따라 즉시 실시간으로 Obsidian에 저장합니다.
6. **신뢰도 항상 표시**
   - 모든 답변 하단에 📊 RAG 신뢰도 배지를 포함합니다.

**답변 형식:**

```
**[전문가 심층 분석 리포트]**
{여기에 풍부한 문단, 리스트, 강조(Bold) 등을 사용하여 논문/전문 보고서 수준의 깊이 있는 해석과 설명을 작성합니다.}

📄 출처: {파일명} (chunk #{n}, score={s:.3f})

---
📊 RAG 신뢰도: {배지} {신뢰도}%  ({검색된_청크_수}개 청크 참조, max_score={max_score:.3f})

🤔 {Socratic Method 기반의 심화 유도 질문}
```

> ⚠️ 신뢰도가 🟠 낮음(20~49%) 또는 🔴 매우 낮음(0~19%)이면 다음 메시지를 강조:
> **"⚡ 신뢰도가 낮습니다. '추가 검색해줘'라고 입력하면 웹에서 최신 자료를 수집합니다."**

---

### Step 2-5: 실시간 Obsidian 저장 (Realtime Save)

답변을 출력한 직후, 사용자의 질문과 방금 생성한 답변 내용을 Obsidian에 실시간으로 기록합니다.
`--realtime` 플래그를 사용하여 마지막 세션에 내용을 이어서 추가합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"

# --realtime 플래그: 현재 세션 블록에 질문/답변 이어서 추가
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{TOPIC}" \
  --content "**Q:** {방금_사용자가_입력한_질문}

**A:** {방금_생성한_답변_내용_전체}" \
  --category "Knowledge_Tutor" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" \
  --realtime

```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}" `
  --content "**Q:** {방금_사용자가_입력한_질문}`n`n**A:** {방금_생성한_답변_내용_전체}" `
  --category "Knowledge_Tutor" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" `
  --realtime
```

</tab>
</tabs>

> 💡 **중요**: 답변을 사용자에게 제공한 후, 반드시 위 명령어를 실행하여 기록을 남기세요.

---

### Step 2-6: 추가 크롤링 요청 처리

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
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
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
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
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

### Step 2-7: 실시간 자동 추가 검색 (범위 초과 시)

사용자 질문이 수집된 자료 범위를 벗어나거나 신뢰도가 자동으로 낮게 측정되면 (신뢰도 < 20%):

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
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
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
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

### Step 2-8: 종료 감지

사용자가 다음 중 하나를 입력하면 Phase 3으로 이동:
- `종료`, `exit`, `quit`, `그만`, `끝`, `done`

---

## Phase 3: 세션 종료 및 총괄 리포트 생성

세션 동안 `--realtime`으로 작성된 Obsidian 노트를 기반으로, 학습한 내용을 총괄적으로 정리하는 **상세 리포트**를 생성하여 노트 마지막에 덧붙입니다. 

1. **컨텍스트 로드**: LLM은 현재 세션에서 다루었던 전체 Q&A 기록을 기반으로 학습 내용을 다시 읽어들입니다.
2. **총괄 리포트 작성**: 단순 요약이 아닌, 이번 세션에서 파악한 기술적 핵심, 연관 관계, 그리고 시사점이 포함된 **"세션 총괄 요약 리포트(Session Executive Summary)"**를 마크다운 형식으로 작성합니다.
3. **Obsidian 반영**: 작성된 리포트를 기존 노트의 마지막에 이어서 저장합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"

# --realtime 플래그를 통해 총괄 리포트를 파일의 맨 마지막에 추가
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{TOPIC}" \
  --content "

---
### 📝 세션 총괄 요약 리포트
{AI가_생성한_상세_총괄_요약_리포트_내용}
" \
  --category "Knowledge_Tutor" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" \
  --realtime
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"

# PowerShell의 줄바꿈을 활용하여 리포트 추가
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}" `
  --content "`n---`n### 📝 세션 총괄 요약 리포트`n{AI가_생성한_상세_총괄_요약_리포트_내용}`n" `
  --category "Knowledge_Tutor" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" `
  --realtime
```

</tab>
</tabs>

> 💡 **중요**: 리포트는 단순한 대화 나열이 아니라, 전문가가 이번 세션에서 탐구한 주제들의 흐름을 한눈에 파악할 수 있도록 구조화된 내용이어야 합니다.

### Step 3-2b: 학습 요약 Mem0 저장

Obsidian 저장 완료 후, 이번 세션 요약을 Mem0 장기 기억에도 저장합니다.
`{UNRESOLVED}`는 튜터링 중 미해결로 표시된 질문들의 목록입니다 (없으면 "없음").
`ANTHROPIC_API_KEY`가 없으면 이 단계를 건너뜁니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
  python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_save.py" \
    --content "{CATEGORY}/{TOPIC} 학습 완료. 핵심 요약: {핵심_요약_SUMMARY}. 미해결: {UNRESOLVED}" \
    --agent "claude" \
    --metadata "{\"workflow\": \"knowledge_tutor\", \"topic\": \"{TOPIC}\", \"category\": \"{CATEGORY}\"}"
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 저장 건너뜀"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

if ($env:ANTHROPIC_API_KEY) {
    $memContent = "{CATEGORY}/{TOPIC} 학습 완료. 핵심 요약: {핵심_요약_SUMMARY}. 미해결: {UNRESOLVED}"
    $memMeta = '{"workflow": "knowledge_tutor", "topic": "{TOPIC}", "category": "{CATEGORY}"}'
    python "$env:AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_save.py" `
      --content "$memContent" `
      --agent "claude" `
      --metadata "$memMeta"
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 저장 건너뜀"
}
```

</tab>
</tabs>

### Step 3-3: 완료 메시지

```
✅ 학습을 완료했습니다!

📁 생성/업데이트된 파일:
  - 누적 노트: {CATEGORY}/{TOPIC}.md  ← 세션이 쌓일수록 기록이 누적됩니다
  - 원본 자료: {CATEGORY}/sources/{safe_topic}/ (총 N개 파일)
  - RAG manifest: {CATEGORY}/rag/{safe_topic}/manifest.json

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
