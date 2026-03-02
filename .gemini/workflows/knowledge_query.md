---
description: knowledge_tutor로 수집된 RAG manifest를 기반으로 기존 자료에서 즉시 질문-답변하는 워크플로우
trigger: /knowledge_query
---

# Knowledge Query Workflow

> 💡 **OS 실행 규칙**: 현재 시스템의 OS를 감지하여 적절한 셸을 사용하세요.
> - **Linux/macOS**: `bash`를 사용하여 실행합니다.
> - **Windows**: `powershell`을 사용하여 실행하며, 변수 및 명령어 구문을 Windows 환경에 맞게 조정합니다.

`knowledge_tutor`로 수집·생성된 `/rag/{topic}/manifest.json`을 조회하여
BM25 RAG 검색으로 사용자 질문에 즉시 답변합니다.

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

- 새로운 웹 검색 없이 기존 수집 자료만 활용 (빠름)
- 질문마다 관련 청크만 추출 → 토큰 절감 (~94%)
- 여러 토픽을 동시에 또는 선택적으로 검색 가능
- RAG manifest가 없으면 자동으로 `knowledge_tutor` 수집 흐름 실행

---

## Step 0: 이전 세션 문맥 로드 (Mem0)

토픽 선택 전, Mem0에서 관련 이전 기억을 검색합니다.
`ANTHROPIC_API_KEY`가 없으면 이 단계를 건너뜁니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
  python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" \
    --query "{TOPIC 또는 사용자 입력 쿼리}" \
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
      --query "{TOPIC 또는 사용자 입력 쿼리}" `
      --limit 3
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — 이전 세션 로드 건너뜀"
}
```

</tab>
</tabs>

---

## Phase 1: RAG Manifest 조회 및 토픽 선택

### Step 1-1: 기존 RAG 목록 확인

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드 및 AGENT_ROOT 설정
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

AGENT_DIR="$OBSIDIAN_VAULT_PATH"

# 등록된 RAG manifest 목록 출력 — 카테고리별로 그룹화
python3 -c "
import os, json, math
agent_dir = '$AGENT_DIR'
print(f'{'식별자 (Category/SafeTopic)':<45} {'Topic':<35} {'파일':<5} {'KB':<6} {'Updated'}')
print('-' * 105)
if os.path.exists(agent_dir):
    for category in sorted(os.listdir(agent_dir)):
        cat_dir = os.path.join(agent_dir, category)
        if not os.path.isdir(cat_dir):
            continue
        
        printed_header = False
        # cat_dir 내의 폴더들을 topic으로 간주하고 rag/manifest.json 확인
        for d in sorted(os.listdir(cat_dir)):
            topic_dir = os.path.join(cat_dir, d)
            if not os.path.isdir(topic_dir):
                continue
                
            manifest_path = os.path.join(topic_dir, 'rag', 'manifest.json')
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    m = json.load(f)
                if not printed_header:
                    print(f'[{category}]')
                    printed_header = True
                identifier = f'{category}/{m.get(\"safe_topic\", d)}'
                size_kb = math.ceil(m.get('total_bytes', 0) / 1024)
                print(f'  {identifier:<43} {m.get(\"topic\", \"\")[:33]:<35} {m.get(\"file_count\", 0):<5} {size_kb:<6} {m.get(\"updated\", \"\")[:10]}')
            except Exception:
                continue
"
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

$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$AGENT_DIR_PY = $AGENT_DIR -replace '\\', '/'

# 등록된 RAG manifest 목록 출력 — 카테고리별로 그룹화
python -c "
import os, json, math
agent_dir = '$AGENT_DIR_PY'
print(f'{'식별자 (Category/SafeTopic)':<45} {'Topic':<35} {'파일':<5} {'KB':<6} {'Updated'}')
print('-' * 105)
if os.path.exists(agent_dir):
    for category in sorted(os.listdir(agent_dir)):
        cat_dir = os.path.join(agent_dir, category)
        if not os.path.isdir(cat_dir):
            continue
        
        printed_header = False
        for d in sorted(os.listdir(cat_dir)):
            topic_dir = os.path.join(cat_dir, d)
            if not os.path.isdir(topic_dir):
                continue

            manifest_path = os.path.join(topic_dir, 'rag', 'manifest.json')
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    m = json.load(f)
                if not printed_header:
                    print(f'[{category}]')
                    printed_header = True
                identifier = f'{category}/{m.get(\"safe_topic\", d)}'
                size_kb = math.ceil(m.get('total_bytes', 0) / 1024)
                print(f'  {identifier:<43} {m.get(\"topic\", \"\")[:33]:<35} {m.get(\"file_count\", 0):<5} {size_kb:<6} {m.get(\"updated\", \"\")[:10]}')
            except Exception:
                continue
"
```

</tab>
</tabs>

> **예시 출력:**
> ```
> Topic                                    Files  Size_KB  Updated              SafeTopic
> ------------------------------------------------------------------------------------------
> Mamba SSM architecture                   6      185      2026-02-19T15:48:00  Mamba_SSM_architecture...
> NVIDIA 자율주행 기술 특징과 동향            6      142      2026-02-19T16:15:00  NVIDIA__________
> ```

---

### Step 1-2: 사용자 토픽 선택

사용자에게 질문합니다:

> **"어떤 주제를 검색하시겠습니까?**
> 위 목록의 **식별자** (`Category/SafeTopic`)를 입력하거나, 카테고리명만 입력해 해당 범주 전체를 검색합니다."

#### 입력 유형별 처리

| 입력 | 처리 |
|------|------|
| `NVBit/safe_topic` (식별자 완전 일치) | 해당 manifest 로드 → Step 1-3 |
| `NVBit` (카테고리명만) | 해당 카테고리의 모든 manifest source_dirs 합산 |
| `전체` 또는 `all` | 전체 카테고리 모든 manifest 합산 |
| `NVBit/..., PyTorch/...` (쉼표 구분) | 해당 manifest들 병합 |
| 목록에 **없는** 새 주제 | Step 1-4 (RAG 생성 흐름 실행) |

---

### Step 1-3: Manifest에서 소스 경로 로드

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# SELECTION 형식: "Category/safe_topic" (Step 1-1 목록의 식별자)
SELECTION="{선택한_식별자}"
if [ -f .env ]; then set -a; source .env; set +a; fi
CATEGORY="${SELECTION%%/*}"
SAFE_TOPIC="${SELECTION##*/}"
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
MANIFEST_PATH="$AGENT_DIR/$CATEGORY/$SAFE_TOPIC/rag/manifest.json"

if [ -f "$MANIFEST_PATH" ]; then
    eval $(python3 -c "
import json, os
with open('$MANIFEST_PATH', 'r', encoding='utf-8') as f:
    m = json.load(f)
vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
dirs = [os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])]
print(f'SOURCE_DIRS=\"{chr(44).join(dirs)}\"')
print(f'FILE_COUNT={m.get(\"file_count\", 0)}')
print(f'TOTAL_KB={int(m.get(\"total_bytes\", 0)/1024)}')
")
    echo "📂 카테고리: $CATEGORY / 토픽: $SAFE_TOPIC"
    echo "📄 파일 수: $FILE_COUNT개 ($TOTAL_KB KB)"
    echo "📁 소스 경로: $SOURCE_DIRS"
else
    echo "⚠️ manifest를 찾을 수 없습니다: $MANIFEST_PATH"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# SELECTION 형식: "Category/safe_topic" (Step 1-1 목록의 식별자)
$SELECTION = "{선택한_식별자}"
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
$CATEGORY  = $SELECTION.Split('/')[0]
$SAFE_TOPIC = $SELECTION.Split('/', 2)[1]
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$MANIFEST_PATH = "$AGENT_DIR/$CATEGORY/$SAFE_TOPIC/rag/manifest.json"

if (Test-Path $MANIFEST_PATH) {
    $MANIFEST_PATH_PY = $MANIFEST_PATH -replace '\\', '/'

    $manifestData = python -c "
import json, os
with open('$MANIFEST_PATH_PY', 'r', encoding='utf-8') as f:
    m = json.load(f)
vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
dirs = [os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])]
print(f'SOURCE_DIRS={','.join(dirs)}')
print(f'FILE_COUNT={m.get(\"file_count\", 0)}')
print(f'TOTAL_KB={int(m.get(\"total_bytes\", 0)/1024)}')
"
    $manifestData | ForEach-Object {
        $n, $v = $_.Split('=', 2)
        Set-Variable -Name $n -Value $v
    }
    Write-Host "📂 카테고리: $CATEGORY / 토픽: $SAFE_TOPIC"
    Write-Host "📄 파일 수: $FILE_COUNT개 ($TOTAL_KB KB)"
    Write-Host "📁 소스 경로: $SOURCE_DIRS"
} else {
    Write-Host "⚠️ manifest를 찾을 수 없습니다: $MANIFEST_PATH"
}
```

</tab>
</tabs>

---

### Step 1-3b: 이전 학습 기록 확인 및 로드

manifest 로드 직후, 해당 카테고리 폴더에서 이전 학습 기록을 자동 탐색합니다.
이전 기록이 있으면 **어디까지 배웠는지 요약**하여 표시하고, 이어서 학습을 진행합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# CATEGORY, SAFE_TOPIC, TOPIC은 Step 1-3에서 설정된 변수 사용
AGENT_DIR="$OBSIDIAN_VAULT_PATH"

python3 -c "
import os, glob

cat_dir = os.path.join('$AGENT_DIR', '$CATEGORY')
topic = '$TOPIC'
safe_topic = '$SAFE_TOPIC'

# 1. 종합 누적 노트 탐색: knowledge_tutor가 --append로 생성한 파일
cumulative = []
for candidate in [
    os.path.join(cat_dir, topic + '.md'),
    os.path.join(cat_dir, safe_topic + '.md'),
]:
    if os.path.isfile(candidate):
        cumulative.append(candidate)

# 2. 세션 노트 탐색: 날짜_topic 또는 topic_조회 패턴
session_notes = []
for f in glob.glob(os.path.join(cat_dir, f'*{safe_topic}*.md')):
    bn = os.path.basename(f)
    # 누적 노트 자체는 제외
    if bn not in [topic + '.md', safe_topic + '.md']:
        session_notes.append(f)
session_notes.sort(key=os.path.getmtime, reverse=True)

# 결과 출력
found = cumulative + session_notes
if found:
    print('PREV_NOTES_FOUND=true')
    for f in cumulative:
        print(f'CUMULATIVE_NOTE={f}')
    for f in session_notes[:3]:  # 최근 3개만
        print(f'SESSION_NOTE={f}')
else:
    print('PREV_NOTES_FOUND=false')
"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# CATEGORY, SAFE_TOPIC, TOPIC은 Step 1-3에서 설정된 변수 사용
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$AGENT_DIR_PY = $AGENT_DIR -replace '\\', '/'

python -c "
import os, glob

cat_dir = os.path.join('$AGENT_DIR_PY', '$CATEGORY')
topic = '$TOPIC'
safe_topic = '$SAFE_TOPIC'

cumulative = []
for candidate in [
    os.path.join(cat_dir, topic + '.md'),
    os.path.join(cat_dir, safe_topic + '.md'),
]:
    if os.path.isfile(candidate):
        cumulative.append(candidate)

session_notes = []
for f in glob.glob(os.path.join(cat_dir, f'*{safe_topic}*.md')):
    bn = os.path.basename(f)
    if bn not in [topic + '.md', safe_topic + '.md']:
        session_notes.append(f)
session_notes.sort(key=os.path.getmtime, reverse=True)

found = cumulative + session_notes
if found:
    print('PREV_NOTES_FOUND=true')
    for f in cumulative:
        print(f'CUMULATIVE_NOTE={f}')
    for f in session_notes[:3]:
        print(f'SESSION_NOTE={f}')
else:
    print('PREV_NOTES_FOUND=false')
"
```

</tab>
</tabs>

**탐색 결과별 처리:**

| 결과 | 처리 |
|------|------|
| `PREV_NOTES_FOUND=true` + `CUMULATIVE_NOTE` 있음 | 종합 누적 노트를 읽어 이전 학습 이력 요약 → 표시 후 이어서 진행 |
| `PREV_NOTES_FOUND=true` + 세션 노트만 있음 | 가장 최근 세션 노트에서 핵심 요약 추출 → 표시 후 이어서 진행 |
| `PREV_NOTES_FOUND=false` | "이전 학습 기록 없음, 새 세션 시작" 안내 후 Phase 2 진행 |

**이전 기록 발견 시** — 파일 내용을 읽어 다음 형식으로 표시:

```
📖 이전 학습 기록을 불러왔습니다.

[마지막 세션: {최근_날짜}]
{학습한_핵심_개념 bullet 3~7개}

이어서 학습을 진행합니다.
아직 다루지 않은 내용이나 더 깊이 알고 싶은 내용을 질문해 주세요.
```

> **중요**: 이전 기록을 읽을 때는 `CUMULATIVE_NOTE` 파일 전체를 Read 도구로 읽어 세션 이력을 파악한다.
> 세션 노트는 최신 파일 1개만 읽으면 충분하다 (중복 방지).

---

### Step 1-4: RAG 없음 — 자동 수집 흐름 실행 ⭐

조회한 주제의 manifest가 없거나 소스가 손상된 경우,
**`knowledge_tutor` Phase 1 + manifest 생성**을 자동으로 실행합니다.

```
🔍 '{TOPIC}'에 대한 RAG manifest가 없습니다.
   지금 자료를 수집하고 RAG를 생성하시겠습니까? (y/n)
   (어떤 카테고리에 저장할지도 함께 입력해주세요. 예: NVBit, PyTorch)
```

**`y` 입력 시 순서대로 실행:**

#### 1-4-a: Tavily 검색 수집

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드 및 AGENT_ROOT 설정
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
OUTPUT_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

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
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$OUTPUT_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

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

> ⚠️ 수집 결과 품질이 낮으면 `knowledge_tutor` Step 1-5 (Garbage 정리 + 재검색) 절차를 따릅니다.

#### 1-4-b: RAG Manifest 생성

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
OUTPUT_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
RAG_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "{TOPIC}" \
  --sources-dir "$OUTPUT_DIR" \
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
$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$OUTPUT_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"
$RAG_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag"

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$OUTPUT_DIR" `
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

#### 1-4-c: manifest 로드 후 Step 2로 진행

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# Manifest 재로드
MANIFEST_PATH="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag/manifest.json"
SOURCE_DIRS=$(python3 -c "
import json, os
m = json.load(open('$MANIFEST_PATH'))
vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
dirs = [os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])]
print(','.join(dirs))
")
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# Manifest 재로드
$MANIFEST_PATH = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag/manifest.json"
$MANIFEST_PATH_PY2 = $MANIFEST_PATH -replace '\\', '/'
$SOURCE_DIRS = python -c "
import json, os
m = json.load(open(r'$MANIFEST_PATH_PY2'))
vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
dirs = [os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])]
print(','.join(dirs))
"
```

</tab>
</tabs>

---

## Phase 2: RAG Q&A 루프

### Step 2-1: 질문 입력받기

사용자에게 질문합니다:

> **"어떤 내용이 궁금하신가요?"**
> 예: `DRIVE Hyperion 10의 센서 구성은?`, `Mamba의 Selection Mechanism이란?`

이전 학습 기록이 있었다면 (`PREV_NOTES_FOUND=true`), 다음과 같이 구체적인 제안을 추가합니다:

```
💡 이전에 배운 내용을 바탕으로 이어서 배울 수 있는 주제 예시:
  - [이전 세션에서 언급됐지만 깊이 다루지 않은 개념들]
  - [이전 학습 키워드와 연관된 심화 질문]
```

이 제안은 Step 1-3b에서 읽은 이전 학습 기록을 분석하여 Claude가 직접 생성합니다.

---

### Step 2-2: RAG 청크 검색 실행

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 단일 소스 디렉토리 (SOURCE_DIRS가 쉼표로 구분된 문자열일 경우 처리)
IFS=',' read -ra DIRS <<< "$SOURCE_DIRS"

for dir in "${DIRS[@]}"; do
    echo "=== [$dir] 검색 중 ==="
    python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
      --query "{QUESTION}" \
      --sources-dir "$dir" \
      --top-k 5 \
      --chunk-size 1200 \
      --show-stats
      
    if [ $? -ne 0 ]; then
      echo "❌ RAG 검색 중 오류가 발생했습니다."
      exit 1
    fi
done
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

# 단일 소스 디렉토리 (SOURCE_DIRS가 쉼표로 구분된 문자열일 경우 처리)
$DIRS = $SOURCE_DIRS -split ','

foreach ($dir in $DIRS) {
    Write-Host "=== [$dir] 검색 중 ==="
    python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" `
      --query "{QUESTION}" `
      --sources-dir "$dir" `
      --top-k 5 `
      --chunk-size 1200 `
      --show-stats
      
    if ($LASTEXITCODE -ne 0) {
      Write-Host "❌ RAG 검색 중 오류가 발생했습니다."
      exit 1
    }
}
```

</tab>
</tabs>

> 💡 **top-k 조정 가이드:**
> - 간단한 사실 확인 → `--top-k 3`
> - 개념 설명 / 비교 분석 → `--top-k 5` (기본)
> - 복잡한 종합 질문 → `--top-k 8`

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

### Step 2-4: 청크 기반 답변 생성

검색된 청크를 내부 컨텍스트로 활용하여 다음 규칙으로 답변합니다:

1. **근거 기반 답변**: 검색된 청크에 있는 내용을 인용하여 답변
2. **출처 명시**: 답변 마지막에 `📄 출처: {파일명} (chunk #{n}, score={s})` 형식으로 표기
3. **범위 초과 처리**: 청크에 관련 내용이 없으면:
   - `"수집된 자료에 해당 내용이 없습니다."`
   - `→ 다른 토픽 추가 검색 or knowledge_tutor로 신규 수집` 제안
4. **한국어 답변 + 기술 용어 병기**
5. **신뢰도 항상 표시**: 모든 답변 하단에 📊 RAG 신뢰도 배지를 포함

**답변 형식:**

```
{답변 내용}

📄 출처: {파일명} (chunk #{n}, score={s:.3f})
...

---
📊 RAG 신뢰도: {배지} {신뢰도}%  ({검색된_청크_수}개 청크 참조, max_score={max_score:.3f})
```

---

### Step 2-5: 후속 안내

답변 후 항상 안내합니다:

```
[계속]    다른 질문을 입력하세요.
[범위]    다른 토픽도 추가로 검색할까요? (현재: {topic})
[보강]    신뢰도가 낮으면 → "추가 검색해줘" / "더 찾아봐" / "크롤링해줘" 로 웹 검색 실행
[종료]    'exit' 또는 '종료'
```

> ⚠️ 신뢰도가 🟠 낮음(20~49%) 또는 🔴 매우 낮음(0~19%)이면 다음 메시지를 강조 표시:
> **"⚡ 신뢰도가 낮습니다. '추가 검색해줘'라고 입력하면 웹에서 최신 자료를 수집합니다."**

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

SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
SAFE_TOPIC=$(echo "{TOPIC}" | tr ' /' '_')
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
  echo "❌ 추가 크롤링 중 오류가 발생했습니다."
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

$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]', '_'
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
  Write-Host "❌ 추가 크롤링 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

크롤링 완료 후:
1. Step 2-2를 재실행하여 동일 질문으로 RAG 재검색
2. 신뢰도를 다시 계산하여 개선 여부를 사용자에게 표시:
   ```
   🔄 자료 보강 완료: {추가된_파일_수}개 파일 추가됨
   신뢰도 변화: {이전_신뢰도}% → {새_신뢰도}%
   ```
3. 개선된 신뢰도로 답변을 갱신

---

### Step 2-7: 다중 토픽 동시 검색

사용자가 `[범위]`를 요청하거나 처음에 복수 토픽을 지정한 경우:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# Python을 사용하여 여러 manifest의 source_dirs를 합침
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

AGENT_DIR="$OBSIDIAN_VAULT_PATH"

ALL_DIRS=$(python3 -c "
import json, os
agent_dir = '$AGENT_DIR'
# 식별자 형식: 'Category/safe_topic' (쉼표 구분)
identifiers = '{Category1/topic1_safe},{Category2/topic2_safe}'.split(',')
all_dirs = []
for ident in identifiers:
    ident = ident.strip()
    parts = ident.split('/', 1)
    if len(parts) != 2:
        continue
    category, safe_topic = parts
    p = os.path.join(agent_dir, category, safe_topic, 'rag', 'manifest.json')
    if os.path.exists(p):
        m = json.load(open(p))
        vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
        all_dirs.extend([os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])])
print(','.join(all_dirs))
")

IFS=',' read -ra DIRS <<< "$ALL_DIRS"
for dir in "${DIRS[@]}"; do
    echo "=== [$dir] 검색 중 ==="
    python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
      --query "{QUESTION}" \
      --sources-dir "$dir" \
      --top-k 3 \
      --chunk-size 800
      
    if [ $? -ne 0 ]; then
      echo "❌ RAG 검색 중 오류가 발생했습니다."
      exit 1
    fi
done
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

$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"

# Python을 사용하여 여러 manifest의 source_dirs를 합침
# 경로 역슬래시 → 슬래시 변환 (Python 인라인 코드 안전성 확보)
$AGENT_DIR_PY2 = $AGENT_DIR -replace '\\', '/'

$ALL_DIRS_STR = python -c "
import json, os
agent_dir = '$AGENT_DIR_PY2'
# 식별자 형식: 'Category/safe_topic' (쉼표 구분)
identifiers = '{Category1/topic1_safe},{Category2/topic2_safe}'.split(',')
all_dirs = []
for ident in identifiers:
    ident = ident.strip()
    parts = ident.split('/', 1)
    if len(parts) != 2:
        continue
    category, safe_topic = parts
    p = os.path.join(agent_dir, category, safe_topic, 'rag', 'manifest.json')
    if os.path.exists(p):
        m = json.load(open(p))
        vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
        all_dirs.extend([os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])])
print(','.join(all_dirs))
"

$DIRS = $ALL_DIRS_STR -split ','
foreach ($dir in $DIRS) {
    Write-Host "=== [$dir] 검색 중 ==="
    python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" `
      --query "{QUESTION}" `
      --sources-dir "$dir" `
      --top-k 3 `
      --chunk-size 800
      
    if ($LASTEXITCODE -ne 0) {
      Write-Host "❌ RAG 검색 중 오류가 발생했습니다."
      exit 1
    }
}
```

</tab>
</tabs>

---

### Step 2-8: 종료 감지

사용자가 다음 중 하나를 입력하면 Phase 3으로 이동:
- `종료`, `exit`, `quit`, `그만`, `끝`, `done`

---

## Phase 3: 세션 Q&A Obsidian 저장 (전체 내역 포함)

세션 동안의 **모든 질문과 답변(QA_HISTORY)**을 생략 없이 누적하여 저장합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

SAFE_CATEGORY=$(echo "{CATEGORY}" | tr ' /' '_')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"

# --append 플래그: 동일 주제 파일이 있으면 세션 블록 누적 추가, 없으면 새로 생성
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{검색_주제}_조회" \
  --content "{전체_Q&A_기록_QA_HISTORY}" \
  --summary "{핵심_포인트_SUMMARY}" \
  --category "Knowledge_Query" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" \
  --append

# 대시보드 업데이트
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" \
  --agent-dir "$AGENT_DIR" \
  --output "$AGENT_DIR/_Dashboard.md"

if [ $? -ne 0 ]; then
  echo "❌ 세션 저장 또는 대시보드 업데이트 중 오류가 발생했습니다."
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

$SAFE_CATEGORY = "{CATEGORY}" -replace '[ /]', '_'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"

# --append 플래그: 동일 주제 파일이 있으면 세션 블록 누적 추가, 없으면 새로 생성
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{검색_주제}_조회" `
  --content "{전체_Q&A_기록_QA_HISTORY}" `
  --summary "{핵심_포인트_SUMMARY}" `
  --category "Knowledge_Query" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" `
  --append

# 대시보드 업데이트
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" `
  --agent-dir "$AGENT_DIR" `
  --output "$AGENT_DIR/_Dashboard.md"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 세션 저장 또는 대시보드 업데이트 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

> 💡 **중요**: 요약이 아닌 실제 사용자와의 모든 문답 로그를 `{전체_Q&A_기록_QA_HISTORY}`에 포함하여 저장하세요.

### Phase 3-b: Q&A 요약 Mem0 저장

Obsidian 저장 완료 후, 핵심 Q&A를 Mem0 장기 기억에도 저장합니다.
`ANTHROPIC_API_KEY`가 없으면 이 단계를 건너뜁니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
  python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_save.py" \
    --content "{TOPIC} Q&A 세션. 주요 질문: {핵심_질문_목록}. 핵심 답변 요약: {핵심_포인트_SUMMARY}" \
    --agent "claude" \
    --metadata "{\"workflow\": \"knowledge_query\", \"topic\": \"{TOPIC}\"}"
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 저장 건너뜀"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

if ($env:ANTHROPIC_API_KEY) {
    $memContent = "{TOPIC} Q&A 세션. 주요 질문: {핵심_질문_목록}. 핵심 답변 요약: {핵심_포인트_SUMMARY}"
    $memMeta = '{"workflow": "knowledge_query", "topic": "{TOPIC}"}'
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

---

## 예시 세션

```
USER: /knowledge_query

AI: 등록된 RAG 목록:
    식별자 (Category/SafeTopic)                   Topic                              파일  KB    Updated
    ---------------------------------------------------------------------------------------------------------
    [자율주행]
      자율주행/NVIDIA__________                   NVIDIA 자율주행 기술 특징과 동향   6     142   2026-02-19
    [AI]
      AI/Mamba_SSM_architecture_deep_learn...     Mamba SSM architecture             6     185   2026-02-19

    어떤 주제를 검색하시겠습니까?
    (식별자 'Category/SafeTopic' 입력, 카테고리명만 입력 시 해당 범주 전체 검색)

USER: 자율주행/NVIDIA__________

AI: manifest 로드 완료.
    📂 카테고리: 자율주행 / 토픽: NVIDIA__________
    📄 파일: 6개 (142 KB)

    📖 이전 학습 기록을 불러왔습니다.
    [마지막 세션: 2026-02-19]
    - NVIDIA DRIVE 플랫폼 개요 학습
    - DRIVE AGX Orin 아키텍처 파악
    - Hyperion 9 센서 구성 확인

    이어서 학습을 진행합니다.
    💡 이어서 배울 수 있는 주제 예시:
      - DRIVE Hyperion 10의 센서 구성 (Hyperion 9 대비 변경점)
      - DriveOS와 DRIVEWORKS SDK의 차이
      - NVIDIA의 엔드투엔드 자율주행 파이프라인

    어떤 내용이 궁금하신가요?

USER: DRIVE Hyperion 10의 센서 구성은?

AI: [RAG 검색 → chunk #9, score=5.769 발견]

    DRIVE AGX Hyperion 10은 다음 멀티모달 센서를 탑재합니다:
    - HD 카메라 14대 / 레이더 9개 / 라이다 1개 / 초음파 12개

    📄 출처: ...DRIVE_platform_features_..._5_2026-02-19.md (chunk #9, score=5.77)

    [계속] 다른 질문을 입력하세요.
    [범위] 다른 토픽도 추가 검색 가능합니다. (예: AI/Mamba_SSM_... 추가)
    [종료] 'exit'

USER: Mamba SSM과 어떤 차이가 있어?

AI: 현재 토픽(자율주행/NVIDIA)에서 Mamba 관련 내용이 없습니다.
    'AI/Mamba_SSM_architecture_deep_learn...' 식별자도 함께 검색할까요?

USER: 응

AI: [두 토픽 동시 검색 실행...]
    ...

USER: 종료

AI: 세션을 Obsidian에 저장하시겠습니까? (y/n)
```

---

## Notes

- **전제 조건**: `knowledge_tutor`로 수집 + manifest 생성이 먼저 필요
- **폴더 구조**: `{Category}/rag/{safe_topic}/manifest.json`
- **대시보드**: 세션 종료 시 `_Dashboard.md` 자동 업데이트
- **소스 경로 이동 시**: manifest의 `source_dirs`를 수동 수정하거나 재수집
- **의존성**: `rank-bm25` (`pip install rank-bm25`)
- **knowledge_tutor와의 차이**:

| | `knowledge_tutor` | `knowledge_query` |
|---|---|---|
| 웹 검색 | ✅ Tavily + Jina | ❌ (기존 자료만) |
| 속도 | 느림 (수집 포함) | ⚡ 빠름 (로컬 BM25) |
| 용도 | 새 주제 학습 | 기존 자료 즉시 조회 |
| RAG 생성 | ✅ (Step 1-6) | ❌ 없으면 자동 연동 |
