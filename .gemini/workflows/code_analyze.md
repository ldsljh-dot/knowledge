---
created: 2026-03-10
updated: 2026-03-10
description: 코드베이스 구조/아키텍처 분석 → Obsidian 마크다운 문서화 + RAG 인덱싱
trigger: /code_analyze
---

# Code Analyze Workflow

> **OS 실행 규칙**: 현재 시스템의 OS를 감지하여 적절한 셸을 사용하세요.
> - **Linux/macOS**: `bash`를 사용하여 실행합니다.
> - **Windows**: `powershell`을 사용하여 실행하며, 변수 및 명령어 구문을 Windows 환경에 맞게 조정합니다.

코드 저장소의 구조와 아키텍처를 분석하여 Obsidian 마크다운으로 문서화합니다.
1. 대상 코드베이스의 디렉토리 구조 및 언어 감지
2. Layer 식별 및 Class/Struct 분석
3. 종합 분석 문서를 Obsidian에 저장 + RAG용 소스 파일 생성
4. 선택적 인터랙티브 Q&A

---

## Phase 1: 환경 설정 및 대상 지정

### Step 1-1: 환경 점검

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "AGENT_ROOT: $AGENT_ROOT"
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"

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

Write-Host "AGENT_ROOT: $env:AGENT_ROOT"
Write-Host "OBSIDIAN_VAULT_PATH: $env:OBSIDIAN_VAULT_PATH"

try { python -c "import rank_bm25" *>$null } catch {
    Write-Host "Installing dependencies..."
    pip install -r "$env:AGENT_ROOT\requirements.txt"
}
```

</tab>
</tabs>

---

### Step 1-2: 사용자 입력

사용자에게 다음을 순서대로 질문합니다:

1. **"분석할 코드베이스 경로를 입력하세요."**
   예: `/home/jh/projects/vllm`, `.` (현재 디렉토리)
   → `{TARGET_PATH}`에 저장 (상대 경로면 절대 경로로 변환)

2. **"프로젝트 이름을 입력하세요. (엔터 = 디렉토리명 사용)"**
   예: `vLLM`, `KnowledgeEngine`
   → `{PROJECT_NAME}`에 저장

3. **"주요 언어 힌트 (선택, 엔터로 건너뜀)?"**
   예: `Python`, `Go`, `Rust`, `TypeScript`
   → `{LANG_HINT}`에 저장 (비어 있으면 자동 감지)

4. **"분석 범위 필터 (선택, 엔터로 건너뜀)?"**
   특정 디렉토리만 분석하고 싶을 때 지정합니다.
   예: `src/`, `cmd/,internal/`, `packages/core`
   → `{SCOPE_FILTER}`에 저장

---

### Step 1-3: 분석 깊이 선택

사용자에게 질문합니다:

```
분석 깊이를 선택하세요:

  [1] Quick Overview
      - 디렉토리 구조 + Layer 분류 + 핵심 엔트리포인트
      - 소요: 빠름

  [2] Standard (권장)
      - Quick + 주요 Class/Struct 역할 + Layer 간 상호작용 다이어그램
      - 소요: 보통

  [3] Deep
      - Standard + 모든 public 메서드 분석 + 상세 call path + 시퀀스 다이어그램
      - 소요: 오래 걸림

선택 (1/2/3, 기본값=2):
```

→ `{DEPTH}` 변수에 `quick` / `standard` / `deep` 저장

---

### Step 1-4: 대상 검증 및 언어 감지

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
TARGET_PATH="{TARGET_PATH}"

if [ ! -d "$TARGET_PATH" ]; then
    echo "경로가 존재하지 않습니다: $TARGET_PATH"
    exit 1
fi

echo "=== 언어별 파일 수 ==="
echo "Python:     $(find "$TARGET_PATH" -name '*.py' -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/venv/*' -not -path '*/dist/*' -not -path '*/build/*' | wc -l)"
echo "Go:         $(find "$TARGET_PATH" -name '*.go' -not -path '*/.git/*' -not -path '*/vendor/*' | wc -l)"
echo "Rust:       $(find "$TARGET_PATH" -name '*.rs' -not -path '*/.git/*' -not -path '*/target/*' | wc -l)"
echo "TypeScript: $(find "$TARGET_PATH" \( -name '*.ts' -o -name '*.tsx' \) -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/dist/*' | wc -l)"
echo "JavaScript: $(find "$TARGET_PATH" \( -name '*.js' -o -name '*.jsx' \) -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/dist/*' | wc -l)"
echo "Java:       $(find "$TARGET_PATH" -name '*.java' -not -path '*/.git/*' -not -path '*/build/*' | wc -l)"
echo "C/C++:      $(find "$TARGET_PATH" \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) -not -path '*/.git/*' -not -path '*/build/*' | wc -l)"
echo "총 파일 수: $(find "$TARGET_PATH" -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/venv/*' -not -path '*/dist/*' -not -path '*/build/*' | wc -l)"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$TARGET_PATH = "{TARGET_PATH}"

if (-not (Test-Path $TARGET_PATH)) {
    Write-Host "경로가 존재하지 않습니다: $TARGET_PATH"
    exit 1
}

$excludeDirs = @('.git', 'node_modules', '__pycache__', 'venv', 'dist', 'build', 'target', 'vendor')
$allFiles = Get-ChildItem -Path $TARGET_PATH -Recurse -File | Where-Object {
    $path = $_.FullName
    -not ($excludeDirs | Where-Object { $path -like "*\$_\*" })
}

Write-Host "=== 언어별 파일 수 ==="
Write-Host "Python:     $(($allFiles | Where-Object { $_.Extension -eq '.py' }).Count)"
Write-Host "Go:         $(($allFiles | Where-Object { $_.Extension -eq '.go' }).Count)"
Write-Host "Rust:       $(($allFiles | Where-Object { $_.Extension -eq '.rs' }).Count)"
Write-Host "TypeScript: $(($allFiles | Where-Object { $_.Extension -in '.ts','.tsx' }).Count)"
Write-Host "JavaScript: $(($allFiles | Where-Object { $_.Extension -in '.js','.jsx' }).Count)"
Write-Host "Java:       $(($allFiles | Where-Object { $_.Extension -eq '.java' }).Count)"
Write-Host "C/C++:      $(($allFiles | Where-Object { $_.Extension -in '.c','.cpp','.h','.hpp' }).Count)"
Write-Host "총 파일 수: $($allFiles.Count)"
```

</tab>
</tabs>

감지된 언어 정보를 `{DETECTED_LANGS}`에 저장합니다.
`{LANG_HINT}`가 비어 있으면 가장 많은 파일 수의 언어를 `{PRIMARY_LANG}`으로 설정합니다.

---

### Step 1-5: 디렉토리 트리 생성

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
TARGET_PATH="{TARGET_PATH}"

# tree가 설치되어 있으면 사용, 아니면 find로 대체
if command -v tree &>/dev/null; then
    tree "$TARGET_PATH" -L 4 -I '.git|node_modules|__pycache__|venv|dist|build|target|vendor|.tox|.mypy_cache|.pytest_cache|*.egg-info' --dirsfirst
else
    find "$TARGET_PATH" -maxdepth 4 \
        -not -path '*/.git/*' -not -path '*/node_modules/*' \
        -not -path '*/__pycache__/*' -not -path '*/venv/*' \
        -not -path '*/dist/*' -not -path '*/build/*' \
        -not -path '*/target/*' -not -path '*/vendor/*' \
        | head -200 | sort
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$TARGET_PATH = "{TARGET_PATH}"

# PowerShell tree 대체
function Show-Tree {
    param([string]$Path, [int]$MaxDepth = 4, [int]$CurrentDepth = 0)
    $excludeDirs = @('.git', 'node_modules', '__pycache__', 'venv', 'dist', 'build', 'target', 'vendor')
    $indent = "  " * $CurrentDepth

    Get-ChildItem -Path $Path | Where-Object {
        -not ($excludeDirs -contains $_.Name)
    } | ForEach-Object {
        if ($_.PSIsContainer) {
            Write-Host "$indent$($_.Name)/"
            if ($CurrentDepth -lt $MaxDepth) {
                Show-Tree -Path $_.FullName -MaxDepth $MaxDepth -CurrentDepth ($CurrentDepth + 1)
            }
        } else {
            Write-Host "$indent$($_.Name)"
        }
    }
}

Show-Tree -Path $TARGET_PATH -MaxDepth 4
```

</tab>
</tabs>

생성된 트리를 `{DIR_TREE}`에 저장합니다.

---

## Phase 2: 코드베이스 분석 (점진적/청크 단위)

### Step 2-1: 엔트리포인트 및 설정 파일 읽기

대상 코드베이스에서 다음 파일을 찾아 읽습니다 (존재하는 것만):

**프로젝트 설정:**
- `README.md`, `README.rst`
- `setup.py`, `setup.cfg`, `pyproject.toml` (Python)
- `Cargo.toml` (Rust)
- `package.json` (JS/TS)
- `go.mod`, `go.sum` (Go)
- `pom.xml`, `build.gradle` (Java)
- `CMakeLists.txt` (C/C++)

**빌드/배포:**
- `Makefile`, `Dockerfile`, `docker-compose.yml`
- `.github/workflows/` (CI/CD)

**메인 진입점:**
- `main.py`, `app.py`, `__main__.py`, `manage.py` (Python)
- `cmd/`, `main.go` (Go)
- `src/main.rs`, `src/lib.rs` (Rust)
- `src/index.ts`, `src/index.js`, `src/App.tsx` (JS/TS)
- `src/main/java/**/Application.java` (Java)

> LLM은 위 파일들을 Read 도구로 직접 읽고, 프로젝트의 목적·의존성·빌드 방식을 파악합니다.
> `{SCOPE_FILTER}`가 지정된 경우 해당 디렉토리 내의 파일만 분석합니다.

파악한 내용을 `{PROJECT_OVERVIEW}`에 정리합니다:
- 프로젝트 목적/설명
- 주요 의존성
- 빌드/실행 방법
- 진입점 파일 경로

---

### Step 2-2: Layer 식별

디렉토리별로 대표 파일 2~3개를 읽고 아키텍처 Layer를 분류합니다.

**분류 기준:**

| Layer | 설명 | 일반적인 디렉토리명 |
|-------|------|---------------------|
| API/Interface | HTTP 핸들러, CLI, gRPC 서비스 정의 | `api/`, `handlers/`, `routes/`, `cmd/`, `cli/` |
| Service/Business Logic | 핵심 비즈니스 로직 | `service/`, `core/`, `domain/`, `engine/` |
| Data/Repository | DB 접근, 저장소 패턴 | `repository/`, `db/`, `models/`, `store/` |
| Infrastructure | 외부 서비스 연동, 설정 | `infra/`, `config/`, `adapters/` |
| Utils/Common | 공용 유틸리티 | `utils/`, `common/`, `helpers/`, `lib/` |
| Tests | 테스트 코드 | `tests/`, `test/`, `*_test.go`, `*_test.rs` |
| Build/Deploy | 빌드·배포 설정 | `scripts/`, `deploy/`, `.github/`, `docker/` |
| Docs | 문서 | `docs/`, `doc/` |

각 디렉토리에 대해:
1. 디렉토리 내 파일 목록 확인
2. 대표 파일 2~3개 읽기
3. 위 분류 기준에 따라 Layer 배정

결과를 `{LAYER_MAP}` (디렉토리 → Layer 매핑)에 저장합니다.

---

### Step 2-3: Class/Struct 분석

언어별 패턴으로 Class/Struct 정의를 검색합니다:

| 언어 | 검색 패턴 |
|------|-----------|
| Python | `class X:`, `class X(Base):` |
| Go | `type X struct`, `type X interface` |
| Rust | `struct X`, `enum X`, `trait X`, `impl X` |
| TypeScript/JavaScript | `class X`, `interface X`, `type X =` |
| Java | `class X`, `interface X`, `enum X` |
| C/C++ | `class X`, `struct X` |

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
TARGET_PATH="{TARGET_PATH}"

# 예시: Python 클래스 검색
grep -rn "^class " "$TARGET_PATH" \
    --include="*.py" \
    --exclude-dir=".git" --exclude-dir="__pycache__" \
    --exclude-dir="venv" --exclude-dir="node_modules" \
    --exclude-dir="build" --exclude-dir="dist" \
    | head -100

# 예시: Go struct 검색
grep -rn "^type .* struct" "$TARGET_PATH" \
    --include="*.go" \
    --exclude-dir=".git" --exclude-dir="vendor" \
    | head -100
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$TARGET_PATH = "{TARGET_PATH}"

# 예시: Python 클래스 검색
Get-ChildItem -Path $TARGET_PATH -Recurse -Include *.py |
    Where-Object { $_.FullName -notmatch '(\.git|__pycache__|venv|node_modules|build|dist)' } |
    Select-String -Pattern "^class " | Select-Object -First 100

# 예시: Go struct 검색
Get-ChildItem -Path $TARGET_PATH -Recurse -Include *.go |
    Where-Object { $_.FullName -notmatch '(\.git|vendor)' } |
    Select-String -Pattern "^type .* struct" | Select-Object -First 100
```

</tab>
</tabs>

> LLM은 `{PRIMARY_LANG}`에 맞는 패턴을 선택하여 검색합니다. 여러 언어가 혼합된 경우 각각 실행합니다.

**깊이별 분석 수준:**

- **Quick**: 핵심 클래스명과 한 줄 역할 설명만 기록
- **Standard**: 역할(2~5줄) + 주요 메서드 목록 + 의존성 관계
- **Deep**: Standard + 모든 public 메서드 설명 + 내부 호출 추적

검색된 클래스를 파일 단위로 읽어 분석한 결과를 `{CLASS_ANALYSIS}`에 저장합니다.

---

### Step 2-4: Layer 간 상호작용 추적 (Standard/Deep만)

> `{DEPTH}`가 `quick`이면 이 단계를 건너뜁니다.

**cross-layer import 분석:**

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
TARGET_PATH="{TARGET_PATH}"

# 다른 레이어 디렉토리를 import하는 패턴 검색
# Python 예시
grep -rn "^from \|^import " "$TARGET_PATH" \
    --include="*.py" \
    --exclude-dir=".git" --exclude-dir="__pycache__" \
    --exclude-dir="venv" --exclude-dir="test*" \
    | grep -v "^Binary" | head -200

# Go 예시
grep -rn "\".*/" "$TARGET_PATH" \
    --include="*.go" \
    --exclude-dir=".git" --exclude-dir="vendor" \
    | head -200
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$TARGET_PATH = "{TARGET_PATH}"

# Python import 분석
Get-ChildItem -Path $TARGET_PATH -Recurse -Include *.py |
    Where-Object { $_.FullName -notmatch '(\.git|__pycache__|venv|test)' } |
    Select-String -Pattern "^(from |import )" | Select-Object -First 200

# Go import 분석
Get-ChildItem -Path $TARGET_PATH -Recurse -Include *.go |
    Where-Object { $_.FullName -notmatch '(\.git|vendor)' } |
    Select-String -Pattern '".*/"' | Select-Object -First 200
```

</tab>
</tabs>

분석 결과:
1. **의존 방향 정리**: 어떤 Layer가 어떤 Layer를 참조하는지
2. **주요 call path 추적**: 요청 → 핸들러 → 서비스 → 저장소 등의 흐름
3. **데이터 흐름 패턴 식별**: 입력 → 변환 → 출력 경로

결과를 `{INTERACTION_MAP}`에 저장합니다.

---

### Step 2-5: 기능별 범주 그룹핑 (Standard/Deep만)

> `{DEPTH}`가 `quick`이면 이 단계를 건너뜁니다.

Step 2-2~2-4의 분석 결과를 기반으로, 디렉토리/레이어 중심이 아닌 **기능/도메인 중심**으로 재그룹핑합니다.

각 기능에 대해:
- 기능명과 설명
- 관여하는 Layer와 해당 파일 목록
- 주요 데이터 흐름

결과를 `{FEATURE_MAP}`에 저장합니다.

---

## Phase 3: 문서 생성 및 Obsidian 저장

### Step 3-1: 종합 분석 문서 생성

LLM이 아래 구조의 마크다운 문서를 직접 작성합니다. `{DEPTH}`에 따라 포함 여부가 달라지는 섹션이 있습니다.

```markdown
---
created: {TODAY}
updated: {TODAY}
tags: [code-analysis, {PRIMARY_LANG}, {PROJECT_NAME}]
category: Code_Analysis
status: complete
depth: {DEPTH}
---

# {PROJECT_NAME} 코드베이스 분석

## 프로젝트 개요

{PROJECT_OVERVIEW 내용}

## 기술 스택

| 항목 | 내용 |
|------|------|
| 주요 언어 | {PRIMARY_LANG} |
| 프레임워크 | {감지된 프레임워크} |
| 빌드 도구 | {감지된 빌드 도구} |
| 테스트 | {감지된 테스트 프레임워크} |
| CI/CD | {감지된 CI/CD} |

## 디렉토리 구조

```
{DIR_TREE에 주석 추가한 버전}
```

## 아키텍처 Layer

{LAYER_MAP 기반의 각 Layer 설명}

```mermaid
graph TD
    {Layer 간 관계를 표현하는 Mermaid 다이어그램}
```

## Class/Struct 분석

{CLASS_ANALYSIS를 테이블 형태로 정리}

| Class/Struct | 파일 | Layer | 역할 |
|-------------|------|-------|------|
| ... | ... | ... | ... |

## Layer 간 상호작용 (Standard/Deep)

{INTERACTION_MAP 기반 설명}

```mermaid
sequenceDiagram
    {주요 call path를 표현하는 시퀀스 다이어그램}
```

## 기능별 범주 (Standard/Deep)

{FEATURE_MAP 기반 설명}

## 분석 메타데이터

- 분석 일시: {TODAY}
- 분석 깊이: {DEPTH}
- 대상 경로: {TARGET_PATH}
- 총 파일 수: {TOTAL_FILES}
- 주요 언어: {PRIMARY_LANG} ({파일_수}개)
```

> LLM은 위 템플릿을 기반으로, 실제 분석 결과를 채워 완성된 마크다운 문서를 `{ANALYSIS_DOC}` 변수에 저장합니다.

---

### Step 3-2: Obsidian에 저장

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_PROJECT=$(echo "{PROJECT_NAME}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
SAVE_DIR="$AGENT_DIR/Code_Analysis/$SAFE_PROJECT"

python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{PROJECT_NAME}" \
  --content "{ANALYSIS_DOC}" \
  --summary "코드 분석 완료: {PROJECT_NAME} ({DEPTH})" \
  --category "Code_Analysis" \
  --vault-path "$SAVE_DIR" \
  --append

if [ $? -ne 0 ]; then
  echo "Obsidian 저장 중 오류가 발생했습니다."
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

$SAFE_PROJECT = "{PROJECT_NAME}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$SAVE_DIR = "$AGENT_DIR/Code_Analysis/$SAFE_PROJECT"

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{PROJECT_NAME}" `
  --content "{ANALYSIS_DOC}" `
  --summary "코드 분석 완료: {PROJECT_NAME} ({DEPTH})" `
  --category "Code_Analysis" `
  --vault-path "$SAVE_DIR" `
  --append

if ($LASTEXITCODE -ne 0) {
  Write-Host "Obsidian 저장 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

---

### Step 3-3: RAG용 소스 파일 저장

분석 내용을 섹션별로 분리하여 RAG 검색에 최적화된 소스 파일을 생성합니다.
LLM이 직접 파일을 작성합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi

SAFE_PROJECT=$(echo "{PROJECT_NAME}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
SOURCES_DIR="$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/sources"
mkdir -p "$SOURCES_DIR"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$SAFE_PROJECT = "{PROJECT_NAME}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$SOURCES_DIR = "$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/sources"
New-Item -ItemType Directory -Force -Path $SOURCES_DIR | Out-Null
```

</tab>
</tabs>

LLM은 `$SOURCES_DIR`에 다음 파일들을 Write 도구로 직접 생성합니다:

| 파일명 | 내용 |
|--------|------|
| `01_overview_{PROJECT_NAME}_{TODAY}.md` | 프로젝트 개요 + 기술 스택 |
| `02_layers_{PROJECT_NAME}_{TODAY}.md` | 아키텍처 Layer 분류 + Mermaid 다이어그램 |
| `03_classes_{PROJECT_NAME}_{TODAY}.md` | Class/Struct 분석 테이블 |
| `04_interactions_{PROJECT_NAME}_{TODAY}.md` | Layer 간 상호작용 (Standard/Deep만) |
| `05_features_{PROJECT_NAME}_{TODAY}.md` | 기능별 범주 (Standard/Deep만) |

각 파일에는 frontmatter를 포함합니다:
```yaml
---
title: "{섹션명} - {PROJECT_NAME}"
created: {TODAY}
tags: [code-analysis, {PROJECT_NAME}]
---
```

---

### Step 3-4: RAG manifest 생성

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_PROJECT=$(echo "{PROJECT_NAME}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
SOURCES_DIR="$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/sources"
RAG_DIR="$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/rag"

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "{PROJECT_NAME}" \
  --sources-dir "$SOURCES_DIR" \
  --output-dir "$RAG_DIR" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --category "Code_Analysis"

if [ $? -ne 0 ]; then
  echo "Manifest 생성 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_PROJECT = "{PROJECT_NAME}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$SOURCES_DIR = "$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/sources"
$RAG_DIR = "$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/rag"

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "{PROJECT_NAME}" `
  --sources-dir "$SOURCES_DIR" `
  --output-dir "$RAG_DIR" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --category "Code_Analysis"

if ($LASTEXITCODE -ne 0) {
  Write-Host "Manifest 생성 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

---

### Step 3-5: 대시보드 업데이트

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

AGENT_DIR="$OBSIDIAN_VAULT_PATH"

python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" \
  --agent-dir "$AGENT_DIR" \
  --output "$AGENT_DIR/_Dashboard.md"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" `
  --agent-dir "$AGENT_DIR" `
  --output "$AGENT_DIR/_Dashboard.md"
```

</tab>
</tabs>

---

## Phase 4: 인터랙티브 심화 분석 (선택)

### Step 4-1: Q&A 모드 제안

분석 완료 후 사용자에게 제안합니다:

```
분석이 완료되었습니다! 추가로 궁금한 점이 있으신가요?

  - 특정 클래스/모듈에 대한 심화 분석
  - 아키텍처 관련 질문
  - 코드 패턴이나 설계 결정에 대한 질의

RAG 기반으로 생성된 분석 문서에서 답변합니다.
'종료', 'exit', 'quit' 등을 입력하면 세션을 종료합니다.
```

**Q&A 루프:**

사용자 질문이 입력되면:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_PROJECT=$(echo "{PROJECT_NAME}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
SOURCES_DIR="$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/sources"

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
  --query "{USER_QUESTION}" \
  --sources-dir "$SOURCES_DIR" \
  --top-k 5 \
  --chunk-size 1200 \
  --show-stats
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_PROJECT = "{PROJECT_NAME}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$SOURCES_DIR = "$AGENT_DIR/Code_Analysis/$SAFE_PROJECT/sources"

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" `
  --query "{USER_QUESTION}" `
  --sources-dir "$SOURCES_DIR" `
  --top-k 5 `
  --chunk-size 1200 `
  --show-stats
```

</tab>
</tabs>

RAG 결과와 함께 실제 코드베이스를 추가로 읽어 정확한 답변을 제공합니다.

종료 키워드(`종료`, `exit`, `quit`, `그만`, `끝`, `done`) 감지 시 Step 4-2로 이동합니다.

---

### Step 4-2: 완료 메시지

```
코드 분석을 완료했습니다!

저장된 파일:
  - 종합 분석: Code_Analysis/{SAFE_PROJECT}/{PROJECT_NAME}.md
  - RAG 소스: Code_Analysis/{SAFE_PROJECT}/sources/ (N개 파일)
  - RAG manifest: Code_Analysis/{SAFE_PROJECT}/rag/manifest.json
  - 대시보드: _Dashboard.md (업데이트됨)

이 분석 문서에 대해 나중에 질의하려면:
   /knowledge_query → 'Code_Analysis/{SAFE_PROJECT}' 선택

Obsidian에서 확인해보세요!
```

---

## Notes

- **새 Python 스크립트 불필요**: 기존 skill 스크립트(`save_to_obsidian.py`, `create_manifest.py`, `retrieve_chunks.py`, `generate_dashboard.py`)를 재사용
- **RAG 연동**: 분석 결과가 RAG로 인덱싱되어 `/knowledge_query`에서 즉시 질의 가능
- **분석 깊이**: Quick은 빠른 개요, Standard는 균형 잡힌 분석, Deep은 상세 코드 추적
- **범위 필터**: 대규모 코드베이스에서 특정 모듈만 분석할 때 유용
- **의존성**: `rank-bm25` (RAG), `python-dotenv` (환경변수)
