---
created: 2026-03-10
updated: 2026-04-05
description: 프로젝트 자동 인식 + Mem0/Vault Index 기반 지능적 저장 위치 결정 + 코드베이스 Layer 심층 분석 및 Obsidian 동기화
trigger: /code_analyze
---

# Code Analyze Workflow (Context-Aware Layer Deep Dive)

> **OS 실행 규칙**: 현재 시스템의 OS를 감지하여 적절한 셸을 사용하세요.
> - **Linux/macOS**: `bash`를 사용하여 실행합니다.
> - **Windows**: `powershell`을 사용하여 실행하며, 변수 및 명령어 구문을 Windows 환경에 맞게 조정합니다.

현재 작업 디렉토리를 기반으로 프로젝트를 자동 인식하고, **Mem0 장기 기억 → Vault Index 의미 검색 → Obsidian 기존 문서** 순서로 기존 지식을 탐색합니다.
`Code_Analysis`와 같은 고정 폴더를 쓰지 않고, **`vault_search.py`로 관련도 높은 기존 폴더를 찾아서 저장 위치를 지능적으로 결정**합니다.

---

## Phase 0: 환경 설정 및 기존 지식 탐색

### Step 0-1: 환경 점검 및 프로젝트 식별

`.env`를 로드하여 `OBSIDIAN_VAULT_PATH`와 `AGENT_ROOT`를 자동 설정합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -f knowledge/.env ]; then set -a; source knowledge/.env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

TARGET_PATH="$AGENT_ROOT"
PROJECT_NAME=$(basename "$TARGET_PATH")

echo "=== 환경 정보 ==="
echo "AGENT_ROOT:          $AGENT_ROOT"
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"
echo "TARGET_PATH:         $TARGET_PATH"
echo "PROJECT_NAME:        $PROJECT_NAME"

python3 -c "import rank_bm25" 2>/dev/null || { echo "Installing dependencies..."; pip install -r "$AGENT_ROOT/requirements.txt"; }
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

$TARGET_PATH = $env:AGENT_ROOT
$PROJECT_NAME = (Get-Item $TARGET_PATH).Name

Write-Host "=== 환경 정보 ==="
Write-Host "AGENT_ROOT:          $env:AGENT_ROOT"
Write-Host "OBSIDIAN_VAULT_PATH: $env:OBSIDIAN_VAULT_PATH"
Write-Host "TARGET_PATH:         $TARGET_PATH"
Write-Host "PROJECT_NAME:        $PROJECT_NAME"

try { python -c "import rank_bm25" *>$null } catch {
    Write-Host "Installing dependencies..."
    pip install -r "$env:AGENT_ROOT\requirements.txt"
}
```

</tab>
</tabs>

LLM은 `{TARGET_PATH}`, `{PROJECT_NAME}`, `{OBSIDIAN_VAULT_PATH}`를 기억합니다.

---

### Step 0-2: Mem0에서 기존 코드 분석 기억 조회

`ANTHROPIC_API_KEY`가 있으면 이 프로젝트의 기존 코드 분석 기억을 Mem0에서 검색합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -f knowledge/.env ]; then set -a; source knowledge/.env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
  echo "=== Mem0 기억 조회: {PROJECT_NAME} 코드 분석 ==="
  python3 "$AGENT_ROOT/knowledge/.gemini/skills/mem0-memory/scripts/memory_search.py" \
    --query "{PROJECT_NAME} 코드 분석 code_analyze" \
    --limit 5
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 조회 건너뜀"
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
    Write-Host "=== Mem0 기억 조회: {PROJECT_NAME} 코드 분석 ==="
    python "$env:AGENT_ROOT/knowledge/.gemini/skills/mem0-memory/scripts/memory_search.py" `
      --query "{PROJECT_NAME} 코드 분석 code_analyze" `
      --limit 5
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 조회 건너뜀"
}
```

</tab>
</tabs>

#### Mem0 결과 처리

- **기억이 있는 경우**: 기억 목록을 `{MEM0_CONTEXT}`에 저장하고, 사용자에게 이전 분석 이력을 제시.
  > "이 프로젝트의 이전 코드 분석 기억이 있습니다. 기존 분석 경로와 Layer 정보를 참고합니다."

- **기억이 없는 경우**: 신규 분석으로 진행.

---

### Step 0-3: Vault Index로 기존 관련 폴더 의미 검색

Vault Index에서 `{PROJECT_NAME}`과 관련된 기존 폴더를 의미적으로 검색합니다.
이를 통해 **이미 이 프로젝트의 코드 분석이 Obsidian 어디에 저장되어 있는지** 자동으로 탐색합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -f knowledge/.env ]; then set -a; source knowledge/.env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "=== Vault Index: {PROJECT_NAME} 관련 기존 지식 검색 ==="
python3 "$AGENT_ROOT/knowledge/.gemini/skills/vault-index/scripts/vault_search.py" \
  --query "{PROJECT_NAME} code analysis 코드 분석" \
  --top-k 5 \
  --threshold 0.25
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

Write-Host "=== Vault Index: {PROJECT_NAME} 관련 기존 지식 검색 ==="
python "$env:AGENT_ROOT/knowledge/.gemini/skills/vault-index/scripts/vault_search.py" `
  --query "{PROJECT_NAME} code analysis 코드 분석" `
  --top-k 5 `
  --threshold 0.25
```

</tab>
</tabs>

vault_search.py 출력 형식:
```
🔍 관련 지식 (쿼리: "...")
  1. [████░░░░░░] 42%  🗂  Projects
     📂 1-Projects/PyTorchSim/Simulator
  2. [███░░░░░░░] 38%  🗂  Areas
     📂 2-Areas/Architecture/PyTorchSim_Frontend
```

LLM은 이 검색 결과를 `{VAULT_SEARCH_RESULTS}`에 저장합니다.

---

## Phase 1: Layer 선택 및 저장 위치 결정

### Step 1-1: 분석 가능한 Layer 목록 표시

프로젝트 경로 내 하위 디렉토리(Layer 후보)를 나열합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
TARGET_PATH="{TARGET_PATH}"

echo "=== 분석 가능한 주요 Layer (코드베이스 하위 디렉토리) ==="
find "$TARGET_PATH" -maxdepth 1 -type d \
    -not -name ".*" -not -name "build" -not -name "dist" \
    -not -name "node_modules" -not -name "venv" \
    -not -name "__pycache__" -not -name "vault" \
    | sed "s|$TARGET_PATH/||" | grep -v "^$" | sort
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$TARGET_PATH = "{TARGET_PATH}"

Write-Host "=== 분석 가능한 주요 Layer (코드베이스 하위 디렉토리) ==="
Get-ChildItem -Path $TARGET_PATH -Directory | Where-Object {
    $_.Name -notmatch '^\.|build|dist|node_modules|venv|__pycache__|vault'
} | Select-Object -ExpandProperty Name | Sort-Object
```

</tab>
</tabs>

### Step 1-2: Layer 선택 및 기존 지식 매칭

사용자에게 Vault Index 검색 결과와 Layer 목록을 함께 제시합니다:

> **"=== Vault 내 기존 관련 지식 ==="**
> 1. [42%] 📂 1-Projects/PyTorchSim/Simulator  (updated: 2026-03-15)
> 2. [38%] 📂 2-Areas/Architecture/PyTorchSim_Frontend
>
> **"=== 분석 가능한 Layer ==="**
> AsmParser, PyTorchSimFrontend, Scheduler, Simulator, TOGSim, ...
>
> **"어느 Layer를 분석하거나 업데이트하시겠습니까?"**
> - Vault에 이미 관련 폴더가 있는 Layer → **업데이트 모드** (기존 문서 병합)
> - 신규 Layer → **신규 분석 모드**
> - `Root` → 프로젝트 전체 최상위 구조 훑기

→ 사용자의 입력을 `{SELECTED_LAYER}`에 저장합니다.
(`Root` 선택 시 `{ANALYSIS_PATH} = {TARGET_PATH}`, 특정 Layer 선택 시 `{ANALYSIS_PATH} = {TARGET_PATH}/{SELECTED_LAYER}`)

---

### Step 1-3: 저장 위치 결정 (Vault Index 기반 — knowledge_tutor 동일 방식)

선택된 Layer에 대해 Vault Index 검색을 재수행하여 **정확한 저장 위치**를 결정합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -f knowledge/.env ]; then set -a; source knowledge/.env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "=== 저장 위치 결정: {PROJECT_NAME} {SELECTED_LAYER} ==="

# PARA 폴더 구조 표시
echo "=== PARA 지식 구조 ==="
for para in "1-Projects" "2-Areas" "3-Resources"; do
  echo ""
  echo "[$para]"
  find "$OBSIDIAN_VAULT_PATH/$para" -mindepth 1 -maxdepth 2 -type d -not -path "*/.*" \
    | sed "s|$OBSIDIAN_VAULT_PATH/||" | sort
done

# Vault Index 검색 (Layer 특화)
echo ""
echo "=== Vault 유사 폴더 검색 ==="
python3 "$AGENT_ROOT/knowledge/.gemini/skills/vault-index/scripts/vault_search.py" \
  --query "{PROJECT_NAME} {SELECTED_LAYER} 코드 분석 구조" \
  --top-k 5 \
  --threshold 0.25
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

Write-Host "=== 저장 위치 결정: {PROJECT_NAME} {SELECTED_LAYER} ==="

# PARA 폴더 구조 표시
foreach ($para in @("1-Projects", "2-Areas", "3-Resources")) {
    Write-Host "`n[$para]"
    Get-ChildItem "$env:OBSIDIAN_VAULT_PATH/$para" -Recurse -Depth 2 -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName -replace [regex]::Escape("$env:OBSIDIAN_VAULT_PATH/"), "" } | Sort-Object
}

# Vault Index 검색 (Layer 특화)
Write-Host "`n=== Vault 유사 폴더 검색 ==="
python "$env:AGENT_ROOT/knowledge/.gemini/skills/vault-index/scripts/vault_search.py" `
  --query "{PROJECT_NAME} {SELECTED_LAYER} 코드 분석 구조" `
  --top-k 5 `
  --threshold 0.25
```

</tab>
</tabs>

#### 검색 결과 기반 저장 경로 추천 규칙

| 조건 | 추천 경로 결정 방법 |
|------|-------------------|
| 1위 score ≥ 0.75 (75%) | 해당 폴더와 **동일한 상위 폴더** 사용 (이미 관련 분석이 있으므로 같은 곳에 배치). 예: `1-Projects/PyTorchSim/Simulator` → `{CATEGORY} = 1-Projects/PyTorchSim` |
| 1위 score 0.40~0.74 | 해당 폴더의 상위 경로를 참고하되, **`{SELECTED_LAYER}` 이름으로 새 하위 폴더** 생성. 예: `1-Projects/PyTorchSim/{SELECTED_LAYER}` |
| 1위 score < 0.40 또는 결과 없음 | PARA 폴더 구조와 프로젝트 특성을 LLM이 분석하여 적합한 경로 추천. 기본 추천: `1-Projects/{PROJECT_NAME}` |

**추천 경로 예시 (프로젝트: PyTorchSim, Layer: PyTorchSimFrontend):**
- vault_search 1위: `1-Projects/PyTorchSim/Simulator` (62%)
- 규칙 적용: score 0.40~0.74 → `1-Projects/PyTorchSim/PyTorchSimFrontend`
- `{CATEGORY} = 1-Projects/PyTorchSim`

사용자에게 다음과 같이 제시합니다:

> **"🔍 유사한 기존 지식:**
> 1. [62%] 📂 1-Projects/PyTorchSim/Simulator
> 2. [45%] 📂 2-Areas/Architecture/DNN_Accelerator
>
> ⚠️ **유사도 75% 이상 폴더가 있으면 중복 가능성 안내**
>
> **저장 위치 추천: `1-Projects/PyTorchSim`**
> (실제 저장 경로: `1-Projects/PyTorchSim/{SELECTED_LAYER}/`)
>
> 다른 위치를 원하시면 경로를 직접 입력하세요. (Enter: 추천 경로 사용)
> 새 경로 입력 시 자동으로 폴더가 생성됩니다."**

사용자가 확인하거나 입력한 경로를 `{CATEGORY}` 변수에 저장합니다.

> ⚠️ `{CATEGORY}`는 토픽(Layer) 폴더의 **상위 경로**입니다. 
> 실제 파일 저장 경로: `$OBSIDIAN_VAULT_PATH/{CATEGORY}/{SAFE_LAYER}/`

새 경로인 경우 폴더를 생성합니다:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
SAFE_LAYER=$(echo "{SELECTED_LAYER}" | tr ' /' '_')
mkdir -p "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER/sources"
mkdir -p "$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER/rag"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$SAFE_LAYER = "{SELECTED_LAYER}" -replace '[ /]', '_'
New-Item -ItemType Directory -Force -Path "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER/sources" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER/rag" | Out-Null
```

</tab>
</tabs>

---

### Step 1-4: 기존 지식(Context) 로드

선택된 저장 경로에 이미 분석 문서가 존재하면 읽어와 `{EXISTING_KNOWLEDGE}`에 저장합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
SAFE_LAYER=$(echo "{SELECTED_LAYER}" | tr ' /' '_')
LAYER_DOC="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER/${SAFE_LAYER}.md"

if [ -f "$LAYER_DOC" ]; then
    echo "=== 기존 분석 문서 발견: $LAYER_DOC ==="
    cat "$LAYER_DOC"
else
    echo "기존 문서가 없습니다. 새로 분석을 시작합니다."
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$SAFE_LAYER = "{SELECTED_LAYER}" -replace '[ /]', '_'
$LAYER_DOC = "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER/${SAFE_LAYER}.md"

if (Test-Path $LAYER_DOC) {
    Write-Host "=== 기존 분석 문서 발견: $LAYER_DOC ==="
    Get-Content $LAYER_DOC
} else {
    Write-Host "기존 문서가 없습니다. 새로 분석을 시작합니다."
}
```

</tab>
</tabs>

LLM은 `{EXISTING_KNOWLEDGE}` + `{MEM0_CONTEXT}`를 분석 컨텍스트로 활용하며, Phase 3에서 기존 구조나 수동 메모를 파괴하지 않고 병합(Merge)합니다.

---

### Step 1-5: 분석 깊이 선택

사용자에게 질문합니다:

```
선택한 Layer [{SELECTED_LAYER}]에 대한 분석 깊이를 선택하세요:
  [1] Quick    (구조 파악 및 변경점 가볍게 확인)
  [2] Standard (주요 클래스 분석 및 업데이트 - 권장)
  [3] Deep     (내부 호출 추적 포함 상세 업데이트 - 오래 걸림)
```
→ `{DEPTH}` 변수에 저장.

---

## Phase 2: 특정 Layer 심층 분석 (Deep Dive)

### Step 2-1: Layer 내 언어 감지 및 구조 파악

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
ANALYSIS_PATH="{ANALYSIS_PATH}"
echo "=== [$ANALYSIS_PATH] 내 언어별 파일 수 ==="
echo "Python:        $(find "$ANALYSIS_PATH" -name '*.py' | wc -l)"
echo "C/C++:         $(find "$ANALYSIS_PATH" \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) | wc -l)"
echo "MLIR/TableGen: $(find "$ANALYSIS_PATH" \( -name '*.mlir' -o -name '*.td' \) | wc -l)"

echo "=== [$ANALYSIS_PATH] 구조 트리 ==="
if command -v tree &>/dev/null; then
    tree "$ANALYSIS_PATH" -L 3 -I '.git|build|dist|venv|node_modules|__pycache__' --dirsfirst
else
    find "$ANALYSIS_PATH" -maxdepth 3 | head -100 | sort
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$ANALYSIS_PATH = "{ANALYSIS_PATH}"
Write-Host "=== [$ANALYSIS_PATH] 내 파일 수 ==="
Write-Host "총 파일 수: $( (Get-ChildItem -Path $ANALYSIS_PATH -Recurse -File).Count )"

Write-Host "`n=== [$ANALYSIS_PATH] 구조 트리 ==="
Get-ChildItem -Path $ANALYSIS_PATH -Recurse -Depth 3 |
    Where-Object { $_.FullName -notmatch '(\.git|build|dist|venv|node_modules|__pycache__)' } |
    Select-Object -ExpandProperty FullName | Sort-Object
```

</tab>
</tabs>

감지된 언어를 `{PRIMARY_LANG}`으로, 트리를 `{LAYER_TREE}`에 저장합니다.

### Step 2-2: Layer 내 Class/Struct 집중 추출

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
ANALYSIS_PATH="{ANALYSIS_PATH}"
grep -rn "^\s*class \|^\s*struct " "$ANALYSIS_PATH" \
    --include="*.py" --include="*.cpp" --include="*.h" --include="*.go" \
    --exclude-dir="build" --exclude-dir="test*" \
    | head -100
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$ANALYSIS_PATH = "{ANALYSIS_PATH}"
Get-ChildItem -Path $ANALYSIS_PATH -Recurse -Include *.py, *.cpp, *.h, *.go |
    Where-Object { $_.FullName -notmatch '(build|test)' } |
    Select-String -Pattern '^\s*(class|struct) ' | Select-Object -First 100
```

</tab>
</tabs>

### Step 2-3: Deep 전용 — 함수/의존성 추적

`{DEPTH}` = 3 (Deep) 일 때만 추가 실행합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
ANALYSIS_PATH="{ANALYSIS_PATH}"
echo "=== 함수/메서드 정의 목록 ==="
grep -rn "^\s*def \|^\s*void \|^\s*auto \|^\s*inline " "$ANALYSIS_PATH" \
    --include="*.py" --include="*.cpp" --include="*.h" \
    --exclude-dir="build" --exclude-dir="test*" \
    | head -150

echo "=== import/include 의존성 ==="
grep -rn "^import \|^from \|^#include " "$ANALYSIS_PATH" \
    --include="*.py" --include="*.cpp" --include="*.h" \
    --exclude-dir="build" \
    | sort -u | head -80
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$ANALYSIS_PATH = "{ANALYSIS_PATH}"
Write-Host "=== 함수/메서드 정의 목록 ==="
Get-ChildItem -Path $ANALYSIS_PATH -Recurse -Include *.py, *.cpp, *.h |
    Where-Object { $_.FullName -notmatch '(build|test)' } |
    Select-String -Pattern '^\s*(def |void |auto |inline )' | Select-Object -First 150

Write-Host "`n=== import/include 의존성 ==="
Get-ChildItem -Path $ANALYSIS_PATH -Recurse -Include *.py, *.cpp, *.h |
    Select-String -Pattern '^(import |from |#include )' |
    Select-Object -ExpandProperty Line | Sort-Object -Unique | Select-Object -First 80
```

</tab>
</tabs>

### Step 2-4: ⭐ 핵심 소스 파일 실제 읽기 (품질 핵심 단계)

> ⚠️ **이 단계가 분석 품질을 결정합니다.**
> grep으로 추출한 클래스/함수 **이름만으로는** 충분한 분석이 불가능합니다.
> 반드시 핵심 소스 파일을 `view_file` (또는 `cat`) 도구로 **실제 읽어야** 합니다.

#### 읽기 대상 파일 선정 기준

1. **필수**: Step 2-2에서 발견된 클래스가 포함된 **모든 주요 소스 파일** (테스트/빌드 제외)
2. **Deep 모드**: 해당 Layer의 **모든** `.py`, `.cpp`, `.h` 파일을 읽되, 파일당 최대 800줄
3. 대형 파일(800줄 초과)은 핵심 클래스 정의 주변 200줄을 선별 읽기

#### 읽기 방법

LLM은 `view_file` 도구를 사용하여 각 핵심 소스 파일을 순차적으로 읽습니다.

```
예시: Layer가 Scheduler인 경우
  → view_file: Scheduler/scheduler.py     (전체)
  → view_file: Simulator/simulator.py     (의존성 파일 — import로 발견)
```

#### 읽기 후 LLM이 반드시 정리할 항목

읽은 코드를 바탕으로 아래 **10가지 분석 차원(Dimension)**을 정리하여 `{CODE_ANALYSIS}`에 저장합니다:

| # | 차원 | 정리할 내용 |
|---|------|------------|
| 1 | **Structure** | 디렉토리 구조, 파일별 책임 매핑 |
| 2 | **Class Relationships** | 상속 관계, 컴포지션, 의존성 → **Mermaid classDiagram 생성** |
| 3 | **Control Flow** | 메인 실행 경로, 비동기/동기 패턴 → **Mermaid sequenceDiagram 생성** |
| 4 | **Interface/API** | Public 메서드 시그니처 (파라미터 타입, 반환값, 사용 예시) |
| 5 | **Domain Logic** | 핵심 알고리즘 실제 코드 스니펫 (10줄 이상, 주석 첨부) |
| 6 | **State** | 가변 상태 목록, 라이프사이클 → **Mermaid stateDiagram 생성** |
| 7 | **Performance** | 최적화 패턴 (예: time-skip, caching), 실제 코드로 설명 |
| 8 | **Error Handling** | 예외 처리 패턴 (StopIteration 활용, Fail-Fast 등), 실제 코드 |
| 9 | **Observability** | 로깅/출력 포맷, 디버그 설정일 때의 동작 |
| 10 | **Extension** | 확장 포인트 (플러그인, 상속 가능 지점), 등록 패턴 |

> 💡 **핵심 원칙**: 단순한 클래스/함수 이름 나열이 아닌, **"이 코드가 왜 이렇게 설계되었는가"** 수준의 통찰을 제공해야 합니다.
> 모든 설명에는 **실제 소스 코드 스니펫**(5~30줄)을 반드시 첨부합니다.

---

## Phase 3: 문서 갱신 및 Obsidian 저장 (지식 병합)

### Step 3-1: Layer 분석 문서 (재)생성 및 저장

LLM은 `{EXISTING_KNOWLEDGE}` + `{MEM0_CONTEXT}` + 이번 분석 결과(`{LAYER_TREE}`, `{CODE_ANALYSIS}`)를 종합하여 문서를 Merge합니다.

아래 heredoc으로 Obsidian 파일을 저장합니다.
**파일명**: `{SAFE_LAYER}.md` (Layer 이름 기준)
**저장 경로**: `$OBSIDIAN_VAULT_PATH/{CATEGORY}/{SAFE_LAYER}/{SAFE_LAYER}.md`

> ⚠️ **메인 문서 품질 기준**: 최소 50줄 이상, Mermaid 다이어그램 최소 1개, 실제 코드 스니펫 최소 2개

```bash
TODAY=$(date +%Y-%m-%d)
SAFE_LAYER=$(echo "{SELECTED_LAYER}" | tr ' /' '_')
SAVE_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER"

cat << 'ANALYSIS_EOF' > "$SAVE_DIR/${SAFE_LAYER}.md"
---
created: (기존 문서의 created 유지, 없으면 {TODAY})
updated: {TODAY}
tags: [code-analysis, {PRIMARY_LANG}, {PROJECT_NAME}, {SELECTED_LAYER}]
category: {CATEGORY}
status: complete
depth: {DEPTH}
project: {PROJECT_NAME}
---

# [{PROJECT_NAME}] {SELECTED_LAYER} Layer 분석

## 1. Structure & Interface
- **Layer 개요 및 역할**: (이 Layer가 전체 시스템에서 어떤 책임을 맡는지 2~3문장)
- **디렉토리 구조**: ({LAYER_TREE} 트리 포함)
- **핵심 Class/Struct 명세 및 Public API**: (Mermaid classDiagram 포함, 주요 메서드 시그니처 기술)
  (💡 *상세 Class 속성 및 확장 포인트는 `sources/01_Structure_and_Interface.md` 참조*)

## 2. Data & Control Flow
- **입력 → 출력 경로**: (데이터 변환 단계별 설명)
- **제어 흐름**: (동기/비동기 패턴 설명, Mermaid sequenceDiagram 포함)
  (💡 *상세 흐름 제어 로직은 `sources/02_Data_and_Control_Flow.md` 참조*)

## 3. Domain Logic & State
- **주요 알고리즘**: (핵심 알고리즘 설명 + 실제 코드 스니펫)
- **가변 상태(Mutable State)**: (상태 종류, 전이 조건 설명)
  (💡 *실제 코드 스니펫 및 상태 다이어그램은 `sources/03_Domain_Logic_and_State.md` 참조*)

## 4. NFR & Observability
- **성능 최적화**: (실제 최적화 패턴과 코드)
- **에러 처리**: (예외 처리 전략 설명)
- **관측 가능성**: (로깅 포맷, 디버그 모드)
  (💡 *상세 최적화 로직 및 로그 포맷은 `sources/04_NFR_and_Observability.md` 참조*)

## 5. 분석 메타데이터
- 분석 대상: {ANALYSIS_PATH}
- 분석 깊이: **{DEPTH}**

## 6. 변경 이력 (Update History)
- {TODAY}: 분석 깊이 {DEPTH} 로 코드베이스 최신 동기화 완료.
ANALYSIS_EOF
```

---

### Step 3-2: RAG Sources 파일 생성 (⭐ 품질 핵심)

RAG용 Sources 파일들을 최신 코드를 기반으로 풍부하게 생성합니다.
(경로: `$OBSIDIAN_VAULT_PATH/{CATEGORY}/{SAFE_LAYER}/sources/`)

각 파일을 LLM이 `cat << 'EOF' >` 방식으로 생성합니다:
1. `01_Structure_and_Interface.md`
2. `02_Data_and_Control_Flow.md`
3. `03_Domain_Logic_and_State.md`
4. `04_NFR_and_Observability.md`

> ⚠️ **각 sources/*.md 파일 필수 품질 기준** (이 기준을 충족하지 않으면 분석 실패로 간주):

| 기준 | 최솟값 |
|------|--------|
| 파일 크기 | **최소 2KB** (약 50줄 이상) |
| 실제 코드 스니펫 | **최소 2개**, 각 5~30줄, 핵심 라인에 한글 주석 |
| Mermaid 다이어그램 | **최소 1개** (classDiagram / sequenceDiagram / stateDiagram 중 택) |
| "왜" 수준 설명 | 단순 나열 ❌ → 설계 의도·패턴·트레이드오프 분석 ✅ |
| Frontmatter | title, created, tags 필수 |

#### 각 파일별 생성 지침

**01_Structure_and_Interface.md** → 차원 1, 2, 4, 10
- Layer 역할 2~3문장, 디렉토리 트리
- **`mermaid classDiagram`** (클래스 간 관계, 주요 메서드 시그니처 포함)
- Public API 계약 (파라미터 타입, 반환값, 실제 사용 예시 코드)
- 확장 포인트 (상속/플러그인 등록 코드)

**02_Data_and_Control_Flow.md** → 차원 3
- 입력→변환→출력 경로를 **단계별 표(Table)** 로 정리
- **`mermaid sequenceDiagram`** (모듈 간 상호작용, Blocking/Non-blocking 명시)
- 제어 흐름 핵심 코드 스니펫 (10줄 이상, 각 라인 역할 주석)
- IPC/프로토콜이 있는 경우 명령 체계 문서화

**03_Domain_Logic_and_State.md** → 차원 5, 6
- 핵심 비즈니스 알고리즘 **실제 코드 스니펫** (10줄 이상, 각 블록에 한글 주석)
- 시간/주파수/좌표 등의 도메인 변환 공식이 있으면 코드로 설명
- **`mermaid stateDiagram-v2`** (상태 전이 다이어그램, 전이 조건 레이블 포함)
- 가변 상태(Mutable State) 목록과 라이프사이클 설명

**04_NFR_and_Observability.md** → 차원 7, 8, 9
- 성능 최적화 패턴 실제 코드 (예: Time-skip, Caching, Fast-forward)
- 에러 처리 패턴 코드 (StopIteration 활용, Fail-Fast, 에러 전파 경로)
- 로깅/관측 포맷 실제 출력 예시 (`print` 포맷 문자열 인용)
- 환경 변수/설정에 의한 동작 분기 설명

이후 Manifest를 재구축합니다:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -f knowledge/.env ]; then set -a; source knowledge/.env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_LAYER=$(echo "{SELECTED_LAYER}" | tr ' /' '_')
SAVE_DIR="$OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER"
SOURCES_DIR="$SAVE_DIR/sources"
RAG_DIR="$SAVE_DIR/rag"

python3 "$AGENT_ROOT/knowledge/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "{PROJECT_NAME}_{SELECTED_LAYER}" \
  --sources-dir "$SOURCES_DIR" \
  --output-dir "$RAG_DIR" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --category "{CATEGORY}"
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

$SAFE_LAYER = "{SELECTED_LAYER}" -replace '[ /]', '_'
$SAVE_DIR = "$env:OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_LAYER"
$SOURCES_DIR = "$SAVE_DIR\sources"
$RAG_DIR = "$SAVE_DIR\rag"

python "$env:AGENT_ROOT/knowledge/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "{PROJECT_NAME}_{SELECTED_LAYER}" `
  --sources-dir "$SOURCES_DIR" `
  --output-dir "$RAG_DIR" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --category "{CATEGORY}"
```

</tab>
</tabs>

---

### Step 3-3: Vault Index 갱신

새 지식이 저장되었으므로 Vault Index를 자동 갱신합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -f knowledge/.env ]; then set -a; source knowledge/.env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python3 "$AGENT_ROOT/knowledge/.gemini/skills/vault-index/scripts/vault_index.py"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }
python "$env:AGENT_ROOT/knowledge/.gemini/skills/vault-index/scripts/vault_index.py"
```

</tab>
</tabs>

---

### Step 3-4: 분석 결과 Mem0 저장

Obsidian 저장 완료 후, 이번 분석 요약을 Mem0 장기 기억에도 저장합니다.
`ANTHROPIC_API_KEY`가 없으면 건너뜁니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -f knowledge/.env ]; then set -a; source knowledge/.env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
  TODAY=$(date +%Y-%m-%d)
  SAFE_LAYER=$(echo "{SELECTED_LAYER}" | tr ' /' '_')
  python3 "$AGENT_ROOT/knowledge/.gemini/skills/mem0-memory/scripts/memory_save.py" \
    --content "{PROJECT_NAME}/{SELECTED_LAYER} 코드 분석 완료 ({TODAY}). 분석 깊이: {DEPTH}. 핵심 클래스: {CLASS_ANALYSIS_SUMMARY}. 저장 경로: {CATEGORY}/$SAFE_LAYER/" \
    --agent "claude" \
    --metadata "{\"workflow\": \"code_analyze\", \"project\": \"{PROJECT_NAME}\", \"layer\": \"{SELECTED_LAYER}\", \"depth\": \"{DEPTH}\", \"category\": \"{CATEGORY}\", \"topic\": \"{SELECTED_LAYER}\", \"obsidian_path\": \"{CATEGORY}/$SAFE_LAYER\", \"date\": \"{TODAY}\"}"
  echo "✅ Mem0 저장 완료"
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 저장 건너뜀"
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
    $TODAY = Get-Date -Format "yyyy-MM-dd"
    $SAFE_LAYER = "{SELECTED_LAYER}" -replace '[ /]', '_'
    $memContent = "{PROJECT_NAME}/{SELECTED_LAYER} 코드 분석 완료 ($TODAY). 분석 깊이: {DEPTH}. 핵심 클래스: {CLASS_ANALYSIS_SUMMARY}. 저장 경로: {CATEGORY}/$SAFE_LAYER/"
    $memMeta = "{`"workflow`": `"code_analyze`", `"project`": `"{PROJECT_NAME}`", `"layer`": `"{SELECTED_LAYER}`", `"depth`": `"{DEPTH}`", `"category`": `"{CATEGORY}`", `"topic`": `"{SELECTED_LAYER}`", `"obsidian_path`": `"{CATEGORY}/$SAFE_LAYER`", `"date`": `"$TODAY`"}"
    python "$env:AGENT_ROOT/knowledge/.gemini/skills/mem0-memory/scripts/memory_save.py" `
      --content "$memContent" `
      --agent "claude" `
      --metadata "$memMeta"
    Write-Host "✅ Mem0 저장 완료"
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 저장 건너뜀"
}
```

</tab>
</tabs>


### Step 3-5: log.md 기록

분석 완료 후 `$OBSIDIAN_VAULT_PATH/log.md`에 한 줄 추가합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
echo "## [$(date +%Y-%m-%d)] code_analyze | {PROJECT_NAME}/{SELECTED_LAYER}" >> "$OBSIDIAN_VAULT_PATH/log.md"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$today = Get-Date -Format "yyyy-MM-dd"
Add-Content -Path "$env:OBSIDIAN_VAULT_PATH/log.md" -Value "## [$today] code_analyze | {PROJECT_NAME}/{SELECTED_LAYER}"
```

</tab>
</tabs>

---

## Phase 4: 완료

```
🎉 [{PROJECT_NAME}] - [{SELECTED_LAYER}] Layer의 지식 동기화가 완료되었습니다!

📁 저장/업데이트된 위치:
  - Obsidian 분석 문서: {CATEGORY}/{SAFE_LAYER}/{SAFE_LAYER}.md
  - RAG Sources:       {CATEGORY}/{SAFE_LAYER}/sources/
  - RAG Manifest:      {CATEGORY}/{SAFE_LAYER}/rag/manifest.json
  - Vault Index:       ✅ 갱신 완료
  - Mem0 장기 기억:    ✅ (ANTHROPIC_API_KEY 설정 시)
  - log.md:           ✅ 갱신 완료

💡 변경점이나 동작 원리를 묻고 싶다면 `/knowledge_query`를 사용해 보세요!
💡 다음 /code_analyze 실행 시 Mem0 + Vault Index에서 이번 분석 기억을 자동으로 불러옵니다.
```