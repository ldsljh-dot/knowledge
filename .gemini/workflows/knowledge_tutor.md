---
created: 2026-03-10
updated: 2026-03-10
description: AI Tutor workflow - Tavily 웹 검색 + Socratic 튜터링 + Obsidian 저장 + RAG manifest 생성
trigger: /knowledge_tutor
---
created: 2026-03-10
updated: 2026-03-10

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
created: 2026-03-10
updated: 2026-03-10

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
created: 2026-03-10
updated: 2026-03-10

## Step 0: 이전 세션 문맥 로드 (Mem0) + 추가 학습 여부 결정

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
    --limit 5
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
      --limit 5
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — 이전 세션 로드 건너뜀"
}
```

</tab>
</tabs>

### 결과에 따른 분기

**이전 기억이 있는 경우** — 검색된 기억을 번호 목록으로 사용자에게 제시합니다:

> **"이 주제와 관련된 이전 학습 기록이 있습니다:**
>
> 1. {기억_내용_1} (관련도: {score_1})
> 2. {기억_내용_2} (관련도: {score_2})
> ...
>
> **추가로 웹에서 최신 자료를 검색하시겠습니까?**
> - `예` / `yes` → Step 1-1부터 정상 진행 (Tavily 웹 검색 후 기존 지식과 합산)
> - `아니오` / `no` → 웹 검색 없이 기존 자료로 튜터링"

**`예` 선택 시:** Phase 1 Step 1-1부터 정상 진행

**`아니오` 선택 시:** 아래 절차를 순서대로 수행
1. Step 1-1로 이동하여 PARA 폴더 트리 출력 + vault_search로 유사 폴더 탐색
2. 유사 폴더가 발견된 경우:
   - 해당 폴더의 `sources/` 경로를 `OUTPUT_DIR`로 설정
   - Step 1-6으로 건너뛰어 RAG Manifest를 생성 (기존 sources/ 기반)
   - Phase 2 튜터링 시작 — RAG 소스: 기존 sources/ 파일들
3. 유사 폴더가 없는 경우:
   - Mem0 기억 내용을 LLM 컨텍스트로 유지한 채 Phase 2 진입
   - Phase 2의 RAG 검색(Step 2-2) 대신 Mem0 기억을 참고 자료로 사용하여 답변 생성
   - 답변 시 "📋 참고: Mem0 기억 기반 답변입니다 (RAG 자료 없음)" 표시

**이전 기억이 없는 경우:**

> **"관련 이전 학습 기록이 없습니다. Tavily 웹 검색으로 새 자료를 수집합니다."**
> → Phase 1 Step 1-1부터 정상 진행

---

## Phase 1: 정보 수집

### Step 1-1: 학습 주제 입력 및 저장 위치 결정

사용자에게 학습 주제를 질문합니다:

**"어떤 주제를 학습하시겠습니까?"**
예: `PyTorch autograd 동작 원리`, `CXL memory pooling`, `NVBit 메모리 추적`

사용자의 답변을 `{TOPIC}` 변수에 저장합니다.

---

#### Step 1-1b: 소스 코드 질문 감지 → Code Analyze 연동 ⭐

주제를 분석하여 **특정 코드베이스의 소스 코드 동작**에 관한 학습인지 판단합니다.

**감지 조건** (하나라도 해당하면 코드 학습으로 판단):
- 함수명 · 클래스명 · 메서드명 등 코드 식별자를 포함
- 소스 파일 경로 또는 확장자(`.py`, `.cpp`, `.h` 등) 언급
- "구현 방법", "내부 동작", "소스 코드 분석", "어떻게 동작하는지" 등 구현 수준 학습
- 특정 로컬 프로젝트의 코드 로직/아키텍처 이해가 목적

**판단 후 분기:**

| 상황 | 처리 |
|------|------|
| 코드 학습 + Code_Analysis RAG 있음 | 해당 RAG를 `OUTPUT_DIR`로 사용, Step 1-6(manifest 재생성) 후 Phase 2 진행 |
| 코드 학습 + Code_Analysis RAG **없음** | 아래 안내 후 사용자 확인 |
| 일반 지식 학습 | 감지 단계 건너뜀, 정상 진행 |

**Code_Analysis RAG 없음 시 자동 실행:**

> **"🔍 소스 코드 동작에 관한 학습이 감지되었습니다.**
> 코드 분석 자료가 없으므로 `code_analyze`를 자동으로 실행하여 분석 결과를 축적합니다."

`/code_analyze` 워크플로우를 실행합니다. 완료 후 생성된 RAG manifest를 `OUTPUT_DIR`로 사용하여 자동으로 Phase 2 튜터링으로 복귀합니다.

---

다음으로 PARA 폴더 구조를 출력합니다:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi

echo "=== PARA 지식 구조 ==="
for para in "1-Projects" "2-Areas" "3-Resources"; do
  echo ""
  echo "[$para]"
  find "$OBSIDIAN_VAULT_PATH/$para" -mindepth 1 -maxdepth 2 -type d -not -path "*/.*" \
    | sed "s|$OBSIDIAN_VAULT_PATH/||" | sort
done
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

foreach ($para in @("1-Projects", "2-Areas", "3-Resources")) {
    Write-Host "`n[$para]"
    Get-ChildItem "$env:OBSIDIAN_VAULT_PATH/$para" -Recurse -Depth 2 -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName -replace [regex]::Escape("$env:OBSIDIAN_VAULT_PATH/"), "" } | Sort-Object
}
```

</tab>
</tabs>

폴더 목록 출력과 함께, **Vault Index로 의미적으로 유사한 기존 폴더를 검색**합니다:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" \
  --query "{TOPIC}" \
  --top-k 5 \
  --threshold 0.25
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" `
  --query "{TOPIC}" `
  --top-k 5 `
  --threshold 0.25
```

</tab>
</tabs>

vault_search.py 출력 형식은 다음과 같습니다 (score는 0~1 코사인 유사도):
```
🔍 관련 지식 (쿼리: "...")
  1. [████░░░░░░] 42%  🗂  Areas
     📂 2-Areas/LLM/Memory/AI_Agent_Memory_Survey
  2. [███░░░░░░░] 38%  🗂  Areas
     📂 2-Areas/LLM/Memory/mem0
```

검색 결과를 파싱하여 **저장 위치 추천 경로**를 다음 규칙으로 결정합니다:

| 조건 | 추천 경로 결정 방법 |
|------|-------------------|
| 1위 score ≥ 0.75 (75%) | 해당 폴더와 **동일한 상위 폴더** 사용. 예: `2-Areas/LLM/Memory/mem0` → `2-Areas/LLM/Memory` |
| 1위 score 0.40~0.74 | 해당 폴더의 상위 폴더를 참고하되, **토픽명으로 새 하위 폴더** 생성. 예: `2-Areas/LLM/Memory/{SAFE_TOPIC}` |
| 1위 score < 0.40 또는 결과 없음 | PARA 폴더 구조와 토픽 키워드를 LLM이 직접 분석하여 적합한 경로 추천 |

**추천 경로 예시 (토픽: "장기기억 메모리"):**
- vault_search 1위: `2-Areas/LLM/Memory/AI_Agent_Memory_Survey` (42%)
- 규칙 적용: score 0.40~0.74 → `2-Areas/LLM/Memory/장기기억_메모리`
- 추천: `2-Areas/LLM/Memory`

사용자에게 다음과 같이 제시합니다:

> **"🔍 유사한 기존 지식:**
> 1. [42%] 📂 2-Areas/LLM/Memory/AI_Agent_Memory_Survey
> 2. [38%] 📂 2-Areas/LLM/Memory/mem0
>
> ⚠️ **유사도 75% 이상 폴더 있을 경우 중복 가능성 안내** (현재: 해당 없음)
>
> **저장 위치 추천: `2-Areas/LLM/Memory`**
> 다른 위치를 원하시면 경로를 직접 입력하세요. (Enter: 추천 경로 사용)
> 새 경로 입력 시 자동으로 폴더가 생성됩니다."**

사용자가 확인하거나 입력한 경로를 `{CATEGORY}` 변수에 저장합니다.
예: `2-Areas/LLM/Models`, `3-Resources/Compiler`, `1-Projects/xPU-Emulator`

> ⚠️ `{CATEGORY}`는 토픽 폴더의 **상위 경로**입니다. 실제 파일 저장 경로는 `$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/` 입니다.

새 경로인 경우 폴더를 생성합니다:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
mkdir -p "$OBSIDIAN_VAULT_PATH/{CATEGORY}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
New-Item -ItemType Directory -Force -Path "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}" | Out-Null
```

</tab>
</tabs>

---
created: 2026-03-10
updated: 2026-03-10

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
created: 2026-03-10
updated: 2026-03-10

### Step 1-3: Tavily 검색 실행

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
OUTPUT_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"

# 검색 실행
python3 "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
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
$OUTPUT_DIR = "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"

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
created: 2026-03-10
updated: 2026-03-10

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
created: 2026-03-10
updated: 2026-03-10

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
OUTPUT_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"

python3 "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
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
$OUTPUT_DIR = "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"

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
created: 2026-03-10
updated: 2026-03-10

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
SOURCES_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"
RAG_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/rag"

python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
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
$SOURCES_DIR = "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"
$RAG_DIR = "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/rag"

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
created: 2026-03-10
updated: 2026-03-10

## Phase 2: 대화형 튜터링

### Step 2-1: 학습 모드 진입 확인

사용자에게 질문합니다:

> **"수집한 정보를 기반으로 학습을 시작하시겠습니까?**  
> 종료하려면 언제든 `종료` 또는 `exit`를 입력하세요."

---
created: 2026-03-10
updated: 2026-03-10

### Step 2-2: 수집된 자료 읽기 (RAG)

전체 파일을 통째로 읽는 대신, **RAG Retriever로 질문과 관련된 청크만** 추출합니다.

#### Step 2-2-a: 튜터링 시작 시 초기 컨텍스트 확보

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
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

python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
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
created: 2026-03-10
updated: 2026-03-10

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
|---
created: 2026-03-10
updated: 2026-03-10-----|------|------|
| 80~100% | 🟢 높음 | 자료에 충분한 근거 있음 |
| 50~79%  | 🟡 보통 | 부분적 근거, 보완 가능 |
| 20~49%  | 🟠 낮음 | 관련 자료 부족, 추가 검색 권장 |
| 0~19%   | 🔴 매우 낮음 | 자료 없음, 반드시 추가 검색 필요 |

---
created: 2026-03-10
updated: 2026-03-10

### Step 2-4: Interactive Tutoring 루프 (심층 해석 및 지식 합성)

수집된 자료를 **내부 컨텍스트**로 활용하며 다음 규칙으로 튜터링을 진행합니다. 단순 문답이 아니라, 전문가가 논문 수준의 리포트를 작성하듯 **깊이 있는 해석과 통찰**을 제공해야 합니다.

#### 튜터링 핵심 규칙

1. **심층 해석 및 확장 (Detailed Synthesis)**
   - 사용자의 질문이나 단편적인 키워드를 표면적으로만 대답하지 마십시오.
   - 검색된 RAG 데이터를 바탕으로 그 이면의 아키텍처적, 수학적, 기술적 원리와 병목, 시사점 등을 상세히 구조화하여 설명합니다. (예: [원리 설명] - [구조적 특징] - [한계 및 해결책])
2. **Socratic Method 연계**
   - 방대하고 깊이 있는 지식을 전달한 후, 유도 질문을 마지막에 제시합니다.
   - 유도 질문 난이도 기준: 방금 설명한 개념에서 한 단계 더 나아가는 수준 (예: "왜 이 방식이 기존 방식보다 효율적인지 수식으로 설명할 수 있나요?")
   - **미해결 판단**: 사용자가 답변을 못하거나 "모르겠다", "이해 안 된다"고 하면 해당 질문을 `{UNRESOLVED}` 목록에 추가합니다. `{UNRESOLVED}`는 세션 종료(Phase 3) 시 Mem0에 저장됩니다.
3. **정확성과 출처 명시**
   - 수집된 자료에 근거해 학술적/기술적으로 정확하게 답변합니다.
   - 불확실한 내용은 "추가 검색이 필요합니다"라고 명시합니다.
4. **한국어 응답 + 기술 용어 병기**
   - 예: *"자기 수정형 타이탄(Self-Modifying Titans)은 연속체 메모리 시스템(Continuum Memory System)과 결합하여..."*
5. **학습 대화 기록**
   - 모든 심층 답변과 분석 내용은 LLM 컨텍스트에 유지합니다. 세션 종료 시(Phase 3) 정제된 위키 페이지로 일괄 저장됩니다.
6. **신뢰도 항상 표시**
   - 모든 답변 하단에 📊 RAG 신뢰도 배지를 포함합니다.

**답변 형식:**

```
**[전문가 심층 분석 리포트]**
{여기에 풍부한 문단, 리스트, 강조(Bold) 등을 사용하여 논문/전문 보고서 수준의 깊이 있는 해석과 설명을 작성합니다.}

📄 출처: {파일명} (chunk #{n}, score={s:.3f})

---
created: 2026-03-10
updated: 2026-03-10
📊 RAG 신뢰도: {배지} {신뢰도}%  ({검색된_청크_수}개 청크 참조, max_score={max_score:.3f})

🤔 {Socratic Method 기반의 심화 유도 질문}
```

> ⚠️ 신뢰도가 🟠 낮음(20~49%) 또는 🔴 매우 낮음(0~19%)이면 다음 메시지를 강조:
> **"⚡ 신뢰도가 낮습니다. '추가 검색해줘'라고 입력하면 웹에서 최신 자료를 수집합니다."**

---
created: 2026-03-10
updated: 2026-03-10

### Step 2-5: 자동 보강 (신뢰도 낮을 때)

답변 출력 직후, RAG 신뢰도와 질문 유형을 동시에 확인합니다:

| 조건 | 처리 |
|------|------|
| 신뢰도 < 50% + **코드 질문** 감지 | `code_analyze` 자동 실행 → RAG 갱신 → Step 2-2로 복귀 |
| 신뢰도 < 20% + 일반 질문 | Tavily 추가 웹 검색 자동 실행 → Step 2-2로 복귀 |
| 신뢰도 ≥ 20% (일반) / ≥ 50% (코드) | 이 단계 건너뜀 → Step 2-6으로 |

**코드 질문 + 신뢰도 < 50% 시 자동 실행:**
> "🔍 코드 관련 질문이며 RAG 신뢰도가 낮습니다. `code_analyze`를 자동으로 실행하여 분석 결과를 축적합니다..."

`/code_analyze` 워크플로우를 실행합니다. 완료 후 생성된 RAG manifest를 `OUTPUT_DIR`에 추가하여 Step 2-2-b로 복귀합니다.

**일반 질문 + 신뢰도 < 20% 시 자동 실행:**
> "⚡ 신뢰도가 너무 낮아 자동으로 추가 자료를 검색합니다..."

검색 쿼리: 현재 사용자 질문(`{USER_QUESTION}`)의 핵심 키워드를 영어로 변환하여 사용

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')

python3 "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
  --query "{USER_QUESTION의_영어_핵심_키워드}" \
  --output-dir "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources" \
  --max-results 3

python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "{TOPIC}" \
  --sources-dir "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources" \
  --output-dir "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/rag" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --category "{CATEGORY}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'

python "$env:AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" `
  --query "{USER_QUESTION의_영어_핵심_키워드}" `
  --output-dir "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources" `
  --max-results 3

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources" `
  --output-dir "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/rag" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --category "{CATEGORY}"
```

</tab>
</tabs>

검색 완료 후 Step 2-2-b로 돌아가 동일 질문으로 RAG 재검색합니다.

---

### Step 2-6: 사용자 요청 추가 크롤링

사용자가 다음 키워드를 입력하면 추가 웹 크롤링을 실행합니다:
- `추가 검색`, `더 찾아봐`, `크롤링해줘`, `웹 검색`, `자료 추가`, `검색 보강`, `search more`

**추가 크롤링 흐름:**

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
OUTPUT_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"
RAG_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/rag"

python3 "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
  --query "{현재_질문_또는_TOPIC}" \
  --output-dir "$OUTPUT_DIR" \
  --max-results 3 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300

python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
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
$OUTPUT_DIR = "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/sources"
$RAG_DIR = "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC/rag"

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
created: 2026-03-10
updated: 2026-03-10

### Step 2-7: 종료 감지

사용자가 다음 중 하나를 입력하면 Phase 3으로 이동:
- `종료`, `exit`, `quit`, `그만`, `끝`, `done`

---
created: 2026-03-10
updated: 2026-03-10

## Phase 3: 세션 종료 및 위키 페이지 생성

세션의 전체 Q&A를 기반으로, 학습한 내용을 **정제된 위키 백과사전 스타일 문서**로 변환하여 Obsidian에 저장합니다.

### Step 3-1: 위키 페이지 작성

LLM은 세션의 전체 Q&A를 바탕으로 **위키 백과사전 스타일**의 문서를 작성합니다.

#### 작성 규칙
- **Q&A 형식 금지**. 백과사전 항목처럼 서술합니다.
- `[[wikilink]]`로 관련 개념을 연결합니다.
- 코드 예제가 있다면 설명 자료로 재구성합니다.
- 세션에서 다룬 모든 핵심 내용을 빠짐없이 포함합니다.
- 한국어로 작성하되, 기술 용어는 영문 병기합니다.

#### 위키 페이지 구조 템플릿

```markdown
# {Topic Name}

## Overview
{2-3 문단. 무엇인지, 왜 중요한지, 어떤 맥락에서 사용되는지}

## {Core Concept 1}
{구조화된 설명. [[wikilink]]로 관련 개념 연결}

## {Core Concept 2}
{세션에서 다룬 주제 수만큼 섹션 생성}

## Key Takeaways
- 핵심 포인트 1
- 핵심 포인트 2

## Open Questions
- 미해결 질문 ({UNRESOLVED} 목록 반영, 없으면 섹션 생략)

## Related Topics
- [[Topic A]] — 연결 설명
- [[Topic B]] — 연결 설명
```

> 💡 **중요**: 리포트는 단순한 대화 나열이 아니라, 전문가가 작성한 백과사전 항목처럼 체계적이고 읽기 좋아야 합니다.

### Step 3-2: 위키 페이지 저장

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')

# --wiki 플래그: 정제된 위키 페이지로 저장
python3 "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{TOPIC}" \
  --content "{위키_페이지_전체_내용}" \
  --category "{CATEGORY}" \
  --vault-path "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC" \
  --wiki \
  --sources "{쉼표_구분_소스_파일_경로}" \
  --related-topics "{쉼표_구분_관련_토픽}"
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

$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}" `
  --content "{위키_페이지_전체_내용}" `
  --category "{CATEGORY}" `
  --vault-path "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC" `
  --wiki `
  --sources "{쉼표_구분_소스_파일_경로}" `
  --related-topics "{쉼표_구분_관련_토픽}"
```

</tab>
</tabs>

### Step 3-3: 학습 요약 Mem0 저장

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
    --metadata "{\"workflow\": \"knowledge_tutor\", \"topic\": \"{TOPIC}\", \"category\": \"{CATEGORY}\", \"obsidian_path\": \"{CATEGORY}/{SAFE_TOPIC}\"}"
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
    $memMeta = '{"workflow": "knowledge_tutor", "topic": "{TOPIC}", "category": "{CATEGORY}", "obsidian_path": "{CATEGORY}/{SAFE_TOPIC}"}'
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

### Step 3-4: Vault Index 자동 갱신

새 지식이 저장되었으므로 Vault Index를 갱신합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }
python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py"
```

</tab>
</tabs>

### Step 3-5: log.md 기록

세션 완료 후 `$OBSIDIAN_VAULT_PATH/log.md`에 한 줄 추가합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
echo "## [$(date +%Y-%m-%d)] tutor | {TOPIC}" >> "$OBSIDIAN_VAULT_PATH/log.md"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$today = Get-Date -Format "yyyy-MM-dd"
Add-Content -Path "$env:OBSIDIAN_VAULT_PATH/log.md" -Value "## [$today] tutor | {TOPIC}"
```

</tab>
</tabs>

### Step 3-6: 완료 메시지

```
✅ 학습을 완료했습니다!

📁 생성/업데이트된 파일:
  - 위키 페이지: {CATEGORY}/{SAFE_TOPIC}/{SAFE_TOPIC}.md  ← 정제된 백과사전 스타일 문서
  - 원본 자료: {CATEGORY}/{SAFE_TOPIC}/sources/ (총 N개 파일)
  - RAG manifest: {CATEGORY}/{SAFE_TOPIC}/rag/manifest.json
  - log.md: ✅ 갱신 완료

💡 같은 주제로 다시 학습하면 위키 페이지가 더 풍부하게 업데이트됩니다.
💡 다음에 이 주제를 다시 조회하려면:
   /knowledge_query → '{CATEGORY}/{safe_topic}' 선택

Obsidian에서 확인해보세요! 🎉
```

---
created: 2026-03-10
updated: 2026-03-10

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
