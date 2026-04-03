---
created: 2026-03-10
updated: 2026-03-10
description: knowledge_tutor로 수집된 RAG manifest를 기반으로 기존 자료에서 즉시 질문-답변하는 워크플로우
trigger: /knowledge_query
---
created: 2026-03-10
updated: 2026-03-10

# Knowledge Query Workflow

> 💡 **OS 실행 규칙**: 현재 시스템의 OS를 감지하여 적절한 셸을 사용하세요.
> - **Linux/macOS**: `bash`를 사용하여 실행합니다.
> - **Windows**: `powershell`을 사용하여 실행하며, 변수 및 명령어 구문을 Windows 환경에 맞게 조정합니다.

`knowledge_tutor`로 수집·생성된 `/rag/{topic}/manifest.json`을 조회하여
BM25 RAG 검색으로 사용자 질문에 즉시 답변합니다.

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

- 새로운 웹 검색 없이 기존 수집 자료만 활용 (빠름)
- 질문마다 관련 청크만 추출 → 토큰 절감 (~94%)
- 여러 토픽을 동시에 또는 선택적으로 검색 가능
- RAG manifest가 없으면 자동으로 `knowledge_tutor` 수집 흐름 실행

---
created: 2026-03-10
updated: 2026-03-10

## Step 0: 문맥 로드 (Vault Index + Mem0)

토픽 선택 전, 두 가지 소스에서 관련 기존 지식을 검색합니다.

### Step 0-1: Vault Index 의미 검색

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" \
  --query "{TOPIC 또는 사용자 입력 쿼리}" \
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

python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" `
  --query "{TOPIC 또는 사용자 입력 쿼리}" `
  --top-k 5 `
  --threshold 0.25
```

</tab>
</tabs>

검색 결과를 사용자에게 제시합니다:

> **"🔍 관련 기존 지식:**
> 1. [85%] 📂 2-Areas/LLM/Memory/AI_Agent_Memory_Survey
> 2. [72%] 📂 2-Areas/LLM/Memory/mem0
>
> 이 폴더들의 RAG도 함께 참고하시겠습니까? (yes/no)"**

`yes` 선택 시: 해당 폴더들의 `sources/` 경로를 목록으로 기억해 둡니다.
Phase 2 Step 2-2의 RAG 검색 시 `--sources-dir` 인수에 메인 토픽 sources 경로와 함께 추가 경로들을 반복 실행하여 결과를 합산합니다.

예시 (메인: `2-Areas/LLM/Memory/LMCache/sources`, 추가: `2-Areas/LLM/Memory/mem0/sources`):
```bash
# 메인 소스 검색
python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
  --query "{USER_QUESTION}" \
  --sources-dir "$OBSIDIAN_VAULT_PATH/2-Areas/LLM/Memory/LMCache/sources" \
  --top-k 5

# 추가 소스 검색 (yes 선택한 각 폴더마다 반복)
python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
  --query "{USER_QUESTION}" \
  --sources-dir "$OBSIDIAN_VAULT_PATH/2-Areas/LLM/Memory/mem0/sources" \
  --top-k 3
```
두 결과를 합쳐 score 기준으로 정렬 후 상위 청크를 답변에 활용합니다.

### Step 0-2: Mem0 이전 기억 검색

`ANTHROPIC_API_KEY`가 없으면 건너뜁니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -n "$ANTHROPIC_API_KEY" ]; then
  python3 "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" \
    --query "{TOPIC 또는 사용자 입력 쿼리}" \
    --limit 3
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — 이전 세션 로드 건너뜀"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
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

# 등록된 RAG manifest 목록 출력 — 재귀적 탐색 및 미등록 토픽 제안
python3 -c "
import os, json, math, pathlib
agent_dir = pathlib.Path('$AGENT_DIR')
print(f'{\"식별자 (Path relative to Vault)\":<55} {\"Topic\":<30} {\"파일\":<5} {\"KB\":<6} {\"Updated\"}')
print('-' * 115)

# 1. 기존 RAG manifest 탐색 (rglob으로 깊은 폴더까지)
manifests_found = []
if agent_dir.exists():
    for manifest_path in sorted(agent_dir.rglob('rag/manifest.json')):
        if '.obsidian' in manifest_path.parts: continue
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                m = json.load(f)
            rel_topic_dir = manifest_path.parent.parent.relative_to(agent_dir)
            identifier = str(rel_topic_dir).replace('\\', '/')
            size_kb = math.ceil(m.get('total_bytes', 0) / 1024)
            manifests_found.append({
                'id': identifier,
                'topic': m.get('topic', ''),
                'count': m.get('file_count', 0),
                'kb': size_kb,
                'updated': m.get('updated', '')[:10]
            })
        except Exception: continue

for m in manifests_found:
    print(f'  {m[\"id\"]:<53} {m[\"topic\"][:28]:<30} {m[\"count\"]: <5} {m[\"kb\"]: <6} {m[\"updated\"]}')

# 2. 미등록 폴더 탐색 (Potential Topics: .md 파일이 있으나 rag/manifest.json이 없는 폴더)
print(f'\\n[💡 Potential New Topics (No manifest yet)]')
potential = []
if agent_dir.exists():
    for root, dirs, files in os.walk(agent_dir):
        if 'rag' in dirs or '.git' in root or '.obsidian' in root or 'sources' in root:
            continue
        md_files = [f for f in files if f.endswith('.md')]
        if md_files:
            try:
                rel_path = pathlib.Path(root).relative_to(agent_dir)
                if str(rel_path) == '.': continue
                p_str = str(rel_path).replace('\\', '/')
                # 이미 manifest가 있는 폴더이거나 그 하위인 경우 제외
                if not any(p_str.startswith(m['id']) for m in manifests_found):
                    potential.append(p_str)
            except Exception: continue

for p in sorted(potential)[:15]: # 상위 15개만 표시
    print(f'  - {p}')
if len(potential) > 15:
    print(f'  ... 외 {len(potential)-15}개 더 있음')
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

# 등록된 RAG manifest 목록 출력 — 재귀적 탐색 및 미등록 토픽 제안
python -c "
import os, json, math, pathlib
agent_dir = pathlib.Path(r'$AGENT_DIR_PY')
print(f'{\"식별자 (Path relative to Vault)\":<55} {\"Topic\":<30} {\"파일\":<5} {\"KB\":<6} {\"Updated\"}')
print('-' * 115)

manifests_found = []
if agent_dir.exists():
    for manifest_path in sorted(agent_dir.rglob('rag/manifest.json')):
        if '.obsidian' in manifest_path.parts: continue
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                m = json.load(f)
            rel_topic_dir = manifest_path.parent.parent.relative_to(agent_dir)
            identifier = str(rel_topic_dir).replace('\\', '/')
            size_kb = math.ceil(m.get('total_bytes', 0) / 1024)
            manifests_found.append({
                'id': identifier,
                'topic': m.get('topic', ''),
                'count': m.get('file_count', 0),
                'kb': size_kb,
                'updated': m.get('updated', '')[:10]
            })
        except Exception: continue

for m in manifests_found:
    print(f'  {m[\"id\"]:<53} {m[\"topic\"][:28]:<30} {m[\"count\"]: <5} {m[\"kb\"]: <6} {m[\"updated\"]}')

print(f'\\n[💡 Potential New Topics (No manifest yet)]')
potential = []
if agent_dir.exists():
    for root, dirs, files in os.walk(agent_dir):
        if 'rag' in dirs or '.git' in root or '.obsidian' in root or 'sources' in root:
            continue
        md_files = [f for f in files if f.endswith('.md')]
        if md_files:
            try:
                rel_path = pathlib.Path(root).relative_to(agent_dir)
                if str(rel_path) == '.': continue
                p_str = str(rel_path).replace('\\', '/')
                if not any(p_str.startswith(m['id']) for m in manifests_found):
                    potential.append(p_str)
            except Exception: continue

for p in sorted(potential)[:15]:
    print(f'  - {p}')
if len(potential) > 15:
    print(f'  ... 외 {len(potential)-15}개 더 있음')
"
```

</tab>
</tabs>

> **예시 출력:**
> ```
> Topic                                    Files  Size_KB  Updated              SafeTopic
> ---
created: 2026-03-10
updated: 2026-03-10---------------------------------------------------------------------------------------
> Mamba SSM architecture                   6      185      2026-02-19T15:48:00  Mamba_SSM_architecture...
> NVIDIA 자율주행 기술 특징과 동향            6      142      2026-02-19T16:15:00  NVIDIA__________
> ```

---
created: 2026-03-10
updated: 2026-03-10

### Step 1-2: 사용자 토픽 선택

사용자에게 질문합니다:

> **"어떤 주제를 검색하시겠습니까?**
> 위 목록의 **식별자** (`Path/to/Topic`)를 입력하세요. 목록에 없는 폴더 경로를 직접 입력하여 새로 RAG를 생성할 수도 있습니다."

#### 입력 유형별 처리

| 입력 | 처리 |
|---
created: 2026-03-10
updated: 2026-03-10---|------|
| `Path/to/Topic` (식별자 완전 일치) | 해당 manifest 로드 → Step 1-3 |
| `전체` 또는 `all` | 전체 모든 manifest 합산 (Step 2-7 참조) |
| `Topic1, Topic2` (쉼표 구분) | 해당 manifest들 병합 |
| 목록에 **없는** 경로 | 해당 폴더에 .md 파일이 있으면 Step 1-4 (RAG 생성) |

---
created: 2026-03-10
updated: 2026-03-10

### Step 1-3: Manifest에서 소스 경로 로드

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# SELECTION 형식: "Path/to/Topic" (Step 1-1 목록의 식별자)
SELECTION="{선택한_식별자}"
if [ -f .env ]; then set -a; source .env; set +a; fi
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
MANIFEST_PATH="$AGENT_DIR/$SELECTION/rag/manifest.json"

if [ -f "$MANIFEST_PATH" ]; then
    eval $(python3 -c "
import json, os, pathlib
with open('$MANIFEST_PATH', 'r', encoding='utf-8') as f:
    m = json.load(f)
# source_dirs를 절대경로로 변환
manifest_dir = pathlib.Path('$MANIFEST_PATH').parent
dirs = []
for d in m.get('source_dirs', []):
    p = pathlib.Path(d)
    if not p.is_absolute():
        p = (manifest_dir / p).resolve()
    dirs.append(str(p))
print(f'SOURCE_DIRS=\"{chr(44).join(dirs)}\"')
print(f'FILE_COUNT={m.get(\"file_count\", 0)}')
print(f'TOTAL_KB={int(m.get(\"total_bytes\", 0)/1024)}')
print(f'TOPIC=\"{m.get(\"topic\", \"\")}\"')
")
    echo "📂 토픽 식별자: $SELECTION"
    echo "📝 주제: $TOPIC"
    echo "📄 파일 수: $FILE_COUNT개 ($TOTAL_KB KB)"
else
    echo "⚠️ manifest를 찾을 수 없습니다: $MANIFEST_PATH"
    echo "신규 토픽인 경우 Step 1-4를 진행하세요."
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# SELECTION 형식: "Path/to/Topic" (Step 1-1 목록의 식별자)
$SELECTION = "{선택한_식별자}"
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$MANIFEST_PATH = Join-Path $AGENT_DIR $SELECTION "rag/manifest.json"

if (Test-Path $MANIFEST_PATH) {
    $MANIFEST_PATH_PY = $MANIFEST_PATH -replace '\\', '/'

    $manifestData = python -c "
import json, os, pathlib
with open(r'$MANIFEST_PATH_PY', 'r', encoding='utf-8') as f:
    m = json.load(f)
manifest_dir = pathlib.Path(r'$MANIFEST_PATH_PY').parent
dirs = []
for d in m.get('source_dirs', []):
    p = pathlib.Path(d)
    if not p.is_absolute():
        p = (manifest_dir / p).resolve()
    dirs.append(str(p))
print(f'SOURCE_DIRS={','.join(dirs)}')
print(f'FILE_COUNT={m.get(\"file_count\", 0)}')
print(f'TOTAL_KB={int(m.get(\"total_bytes\", 0)/1024)}')
print(f'TOPIC={m.get(\"topic\", \"\")}')
"
    $manifestData | ForEach-Object {
        $n, $v = $_.Split('=', 2)
        Set-Variable -Name $n -Value $v
    }
    Write-Host "📂 토픽 식별자: $SELECTION"
    Write-Host "📝 주제: $TOPIC"
    Write-Host "📄 파일 수: $FILE_COUNT개 ($TOTAL_KB KB)"
} else {
    Write-Host "⚠️ manifest를 찾을 수 없습니다: $MANIFEST_PATH"
    Write-Host "신규 토픽인 경우 Step 1-4를 진행하세요."
}
```

</tab>
</tabs>

---
created: 2026-03-10
updated: 2026-03-10

### Step 1-3b: 이전 학습 기록 확인 및 로드

manifest 로드 직후, 해당 토픽 폴더에서 이전 학습 기록을 자동 탐색합니다.
이전 기록이 있으면 **어디까지 배웠는지 요약**하여 표시하고, 이어서 학습을 진행합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# SELECTION, TOPIC은 Step 1-3에서 설정된 변수 사용
AGENT_DIR="$OBSIDIAN_VAULT_PATH"

python3 -c "
import os, glob, pathlib

topic_dir = os.path.join('$AGENT_DIR', '$SELECTION')
topic = '$TOPIC'

# 1. 종합 누적 노트 탐색
cumulative = []
for candidate in [
    os.path.join(topic_dir, topic + '.md'),
    os.path.join(topic_dir, os.path.basename('$SELECTION') + '.md'),
]:
    if os.path.isfile(candidate):
        cumulative.append(candidate)

# 2. 세션 노트 탐색
session_notes = []
for f in glob.glob(os.path.join(topic_dir, '*.md')):
    bn = os.path.basename(f)
    if bn not in [topic + '.md', os.path.basename('$SELECTION') + '.md']:
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
<tab label="Windows (PowerShell)">

```powershell
# SELECTION, TOPIC은 Step 1-3에서 설정된 변수 사용
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$AGENT_DIR_PY = $AGENT_DIR -replace '\\', '/'

python -c "
import os, glob, pathlib

topic_dir = os.path.join(r'$AGENT_DIR_PY', r'$SELECTION')
topic = '$TOPIC'

cumulative = []
for candidate in [
    os.path.join(topic_dir, topic + '.md'),
    os.path.join(topic_dir, os.path.basename(r'$SELECTION') + '.md'),
]:
    if os.path.isfile(candidate):
        cumulative.append(candidate)

session_notes = []
for f in glob.glob(os.path.join(topic_dir, '*.md')):
    bn = os.path.basename(f)
    if bn not in [topic + '.md', os.path.basename(r'$SELECTION') + '.md']:
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
|---
created: 2026-03-10
updated: 2026-03-10---|------|
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
created: 2026-03-10
updated: 2026-03-10

### Step 1-4: RAG 없음 — 자동 생성 흐름 실행 ⭐

조회한 주제의 manifest가 없거나 신규 폴더인 경우, RAG manifest를 자동으로 생성합니다.

#### 1-4-a: RAG Manifest 생성 (기존 폴더 활용)

이미 폴더 내에 `.md` 파일들이 있는 경우, 해당 폴더를 소스로 하여 즉시 RAG를 생성합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# SELECTION: "Path/to/Topic"
# TOPIC_NAME: 사용자가 지정할 토픽 이름 (예: "Flash Attention 분석")
SELECTION="{선택한_식별자}"
TOPIC_NAME="{토픽_이름}"

if [ -f .env ]; then set -a; source .env; set +a; fi
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
SOURCE_DIR="$AGENT_DIR/$SELECTION"
RAG_DIR="$SOURCE_DIR/rag"

python "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "$TOPIC_NAME" \
  --sources-dir "$SOURCE_DIR" \
  --output-dir "$RAG_DIR" \
  --vault-path "$OBSIDIAN_VAULT_PATH"

if [ $? -ne 0 ]; then
  echo "❌ Manifest 생성 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$SELECTION = "{선택한_식별자}"
$TOPIC_NAME = "{토픽_이름}"

if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$SOURCE_DIR = Join-Path $AGENT_DIR $SELECTION
$RAG_DIR = Join-Path $SOURCE_DIR "rag"

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "$TOPIC_NAME" `
  --sources-dir "$SOURCE_DIR" `
  --output-dir "$RAG_DIR" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Manifest 생성 중 오류가 발생했습니다."
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
created: 2026-03-10
updated: 2026-03-10

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

이 제안은 Step 1-3b에서 읽은 이전 학습 기록을 분석하여 LLM이 직접 생성합니다. Step 1-3b에서 로드한 파일 내용을 기반으로 "아직 깊이 다루지 않은 개념" 또는 "연관 심화 주제"를 2~4개 제시합니다.

---
created: 2026-03-10
updated: 2026-03-10

### Step 2-2: RAG 청크 검색 실행

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 1. 단일 소스 디렉토리 (SOURCE_DIRS가 쉼표로 구분된 문자열일 경우 처리)
IFS=',' read -ra DIRS <<< "$SOURCE_DIRS"

for dir in "${DIRS[@]}"; do
    echo "=== 🗂️ Obsidian RAG 검색: [$dir] ==="
    python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
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

# 2. Vault 지식 그래프 (Multi-hop 연계 검색)
echo "=== 🕸️ Vault 지식 그래프(Multi-hop) 연계 검색 ==="
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" \
  --query "{QUESTION}" \
  --top-k 3 \
  --threshold 0.3

# 3. Mem0 동적 기억 하이브리드 검색
echo "=== 🧠 Mem0 동적 기억 하이브리드 검색 ==="
if [ -n "$ANTHROPIC_API_KEY" ]; then
  python3 "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" \
    --query "{QUESTION}" \
    --limit 3
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 하이브리드 검색 건너뜀"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

# 1. 단일 소스 디렉토리 (SOURCE_DIRS가 쉼표로 구분된 문자열일 경우 처리)
$DIRS = $SOURCE_DIRS -split ','

foreach ($dir in $DIRS) {
    Write-Host "=== 🗂️ Obsidian RAG 검색: [$dir] ==="
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

# 2. Vault 지식 그래프 (Multi-hop 연계 검색)
Write-Host "=== 🕸️ Vault 지식 그래프(Multi-hop) 연계 검색 ==="
python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" `
  --query "{QUESTION}" `
  --top-k 3 `
  --threshold 0.3

# 3. Mem0 동적 기억 하이브리드 검색
Write-Host "=== 🧠 Mem0 동적 기억 하이브리드 검색 ==="
if ($env:ANTHROPIC_API_KEY) {
    python "$env:AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" `
      --query "{QUESTION}" `
      --limit 3
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 하이브리드 검색 건너뜀"
}
```

</tab>
</tabs>

> 💡 **top-k 조정 가이드:**
> - 간단한 사실 확인 → `--top-k 3`
> - 개념 설명 / 비교 분석 → `--top-k 5` (기본)
> - 복잡한 종합 질문 → `--top-k 8`

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

### Step 2-4: 청크 기반 심층 답변 생성 (Detailed Synthesis)

검색된 청크를 내부 컨텍스트로 활용하여 다음 규칙으로 답변을 생성합니다. 단순한 1~2문장의 답변이 아니라, 전문가가 기존 지식을 재해석하여 **논문/리포트 수준의 상세한 구조화된 답변**을 작성해야 합니다.

1. **심층 해석 및 구조화**: 사용자의 질문에 대해 단순히 "예/아니오"나 단답형으로 대답하지 마십시오. RAG 청크의 세부 원리, 아키텍처 특성, 발생 가능한 문제점 등을 종합하여 [원리] - [상세 분석] - [시사점] 등으로 구조화된 리포트를 작성합니다.
2. **근거 기반 답변**: 검색된 청크에 있는 구체적인 수치나 기술적 팩트를 인용하여 논리를 전개합니다.
3. **출처 명시**: 답변 마지막에 `📄 출처: {파일명} (chunk #{n}, score={s})` 형식으로 표기합니다.
4. **범위 초과 처리**: 청크에 관련 내용이 없으면:
   - `"수집된 자료에 해당 내용이 없습니다."`
   - `→ 다른 토픽 추가 검색 or knowledge_tutor로 신규 수집` 제안
5. **한국어 답변 + 기술 용어 병기**
6. **신뢰도 항상 표시**: 모든 답변 하단에 📊 RAG 신뢰도 배지를 포함합니다.

**답변 형식:**

```
**[전문가 심층 분석 리포트]**
{여기에 풍부한 문단, 리스트, 강조(Bold) 등을 사용하여 질문에 대한 논문/전문 보고서 수준의 깊이 있는 해석과 설명을 작성합니다.}

📄 출처: {파일명} (chunk #{n}, score={s:.3f})
...

---
created: 2026-03-10
updated: 2026-03-10
📊 RAG 신뢰도: {배지} {신뢰도}%  ({검색된_청크_수}개 청크 참조, max_score={max_score:.3f})
```

---
created: 2026-03-10
updated: 2026-03-10

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
  --category "Knowledge_Query" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" \
  --realtime
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

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}" `
  --content "**Q:** {방금_사용자가_입력한_질문}`n`n**A:** {방금_생성한_답변_내용_전체}" `
  --category "Knowledge_Query" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" `
  --realtime
```

</tab>
</tabs>

> 💡 **중요**: 답변을 사용자에게 제공한 후, 반드시 위 명령어를 실행하여 기록을 남기세요.

---
created: 2026-03-10
updated: 2026-03-10

### Step 2-6: 후속 안내

답변 및 저장 완료 후 항상 안내합니다:

```
[계속]    다른 질문을 입력하세요.
[범위]    다른 토픽도 추가로 검색할까요? (현재: {topic})
[보강]    신뢰도가 낮으면 → "추가 검색해줘" / "더 찾아봐" / "크롤링해줘" 로 웹 검색 실행
[종료]    'exit' 또는 '종료'
```

> ⚠️ 신뢰도가 🟠 낮음(20~49%) 또는 🔴 매우 낮음(0~19%)이면 다음 메시지를 강조 표시:
> **"⚡ 신뢰도가 낮습니다. '추가 검색해줘'라고 입력하면 웹에서 최신 자료를 수집합니다."**

---
created: 2026-03-10
updated: 2026-03-10

### Step 2-7: 추가 크롤링 요청 처리

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
created: 2026-03-10
updated: 2026-03-10

### Step 2-8: 다중 토픽 동시 검색

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
created: 2026-03-10
updated: 2026-03-10

### Step 2-9: 종료 감지

사용자가 다음 중 하나를 입력하면 Phase 3으로 이동:
- `종료`, `exit`, `quit`, `그만`, `끝`, `done`

---
created: 2026-03-10
updated: 2026-03-10

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
created: 2026-03-10
updated: 2026-03-10
### 📝 세션 총괄 요약 리포트
{AI가_생성한_상세_총괄_요약_리포트_내용}
" \
  --category "Knowledge_Query" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" \
  --realtime
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

# PowerShell의 줄바꿈을 활용하여 리포트 추가
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}" `
  --content "`n---
created: 2026-03-10
updated: 2026-03-10`n### 📝 세션 총괄 요약 리포트`n{AI가_생성한_상세_총괄_요약_리포트_내용}`n" `
  --category "Knowledge_Query" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" `
  --realtime
```

</tab>
</tabs>

> 💡 **중요**: 리포트는 단순한 대화 나열이 아니라, 전문가가 이번 세션에서 탐구한 주제들의 흐름을 한눈에 파악할 수 있도록 구조화된 내용이어야 합니다.

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
created: 2026-03-10
updated: 2026-03-10

## 예시 세션

```
USER: /knowledge_query

AI: 등록된 RAG 목록:
    식별자 (Category/SafeTopic)                   Topic                              파일  KB    Updated
    ---
created: 2026-03-10
updated: 2026-03-10------------------------------------------------------------------------------------------------------
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
created: 2026-03-10
updated: 2026-03-10

## Notes

- **전제 조건**: `knowledge_tutor`로 수집 + manifest 생성이 먼저 필요
- **폴더 구조**: `{Category}/rag/{safe_topic}/manifest.json`
- **소스 경로 이동 시**: manifest의 `source_dirs`를 수동 수정하거나 재수집
- **의존성**: `rank-bm25` (`pip install rank-bm25`)
- **knowledge_tutor와의 차이**:

| | `knowledge_tutor` | `knowledge_query` |
|---
created: 2026-03-10
updated: 2026-03-10|---|---|
| 웹 검색 | ✅ Tavily + Jina | ❌ (기존 자료만) |
| 속도 | 느림 (수집 포함) | ⚡ 빠름 (로컬 BM25) |
| 용도 | 새 주제 학습 | 기존 자료 즉시 조회 |
| RAG 생성 | ✅ (Step 1-6) | ❌ 없으면 자동 연동 |
