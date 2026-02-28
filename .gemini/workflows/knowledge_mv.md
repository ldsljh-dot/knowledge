---
description: 기존 지식(토픽)을 다른 카테고리로 이동하거나 이름을 변경합니다.
trigger: /knowledge_mv
---

# Knowledge Move Workflow

수집된 지식(sources, RAG, 노트)을 새로운 위치로 이동하거나 이름을 변경합니다.

> ⚠️ **주의**: 이동 작업은 파일 경로를 변경하므로, 다른 노트에서 이 토픽을 참조하는 링크가 깨질 수 있습니다.

---

## Phase 1: 이동 대상 선택

### Step 1-1: 현재 토픽 목록 확인

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"

# 토픽 목록 출력
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/list_topics.py" 
  --agent-dir "$AGENT_DIR"

if [ $? -ne 0 ]; then
  echo "❌ 토픽 목록을 불러오는 중 오류가 발생했습니다."
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

$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"

# 토픽 목록 출력
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/list_topics.py" `
  --agent-dir "$AGENT_DIR"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 토픽 목록을 불러오는 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

---

### Step 1-2: 이동 설정 입력

사용자에게 다음 정보를 입력받습니다:

1. **"이동할 대상 토픽은 무엇입니까?"**
   예: `AI_Study/Transformer_Architecture` (위 목록의 `Category/Topic` 형식)
   변수: `{SOURCE_TOPIC}`

2. **"새로운 카테고리는 무엇입니까?"**
   (변경하지 않으려면 엔터)
   예: `DeepLearning_Basics`
   변수: `{NEW_CATEGORY}`

3. **"새로운 토픽 이름은 무엇입니까?"**
   (변경하지 않으려면 엔터)
   예: `Transformer_Models`
   변수: `{NEW_TOPIC_NAME}`

---

## Phase 2: 이동 실행

### Step 2-1: 스크립트 실행

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 입력값이 비어있으면 기존 값 사용 (Bash 변수 처리)
SRC="{SOURCE_TOPIC}"
NEW_CAT="{NEW_CATEGORY}"
NEW_NAME="{NEW_TOPIC_NAME}"

# 카테고리/이름 추출
OLD_CAT=$(echo "$SRC" | cut -d'/' -f1)
OLD_NAME=$(echo "$SRC" | cut -d'/' -f2)

if [ -z "$NEW_CAT" ]; then NEW_CAT="$OLD_CAT"; fi
if [ -z "$NEW_NAME" ]; then NEW_NAME="$OLD_NAME"; fi

echo "🚀 이동 시작: $SRC -> $NEW_CAT/$NEW_NAME"

python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/move_knowledge.py" 
  --source "$SRC" 
  --dest-category "$NEW_CAT" 
  --dest-topic "$NEW_NAME" 
  --vault-path "$OBSIDIAN_VAULT_PATH"

if [ $? -ne 0 ]; then
  echo "❌ 이동 작업 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$SRC = "{SOURCE_TOPIC}"
$NEW_CAT = "{NEW_CATEGORY}"
$NEW_NAME = "{NEW_TOPIC_NAME}"

# 카테고리/이름 추출 (PowerShell)
$parts = $SRC.Split('/')
$OLD_CAT = $parts[0]
$OLD_NAME = $parts[1]

if (-not $NEW_CAT) { $NEW_CAT = $OLD_CAT }
if (-not $NEW_NAME) { $NEW_NAME = $OLD_NAME }

Write-Host "🚀 이동 시작: $SRC -> $NEW_CAT/$NEW_NAME"

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/move_knowledge.py" `
  --source "$SRC" `
  --dest-category "$NEW_CAT" `
  --dest-topic "$NEW_NAME" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 이동 작업 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

---

## Phase 3: 마무리

### Step 3-1: 대시보드 업데이트

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

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 대시보드 업데이트 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

### Step 3-2: 결과 요약

```
✅ 이동이 완료되었습니다!

📂 변경 사항:
  - 원본: {SOURCE_TOPIC}
  - 대상: {NEW_CATEGORY}/{NEW_TOPIC_NAME}
  - 소스 파일 이동 완료
  - RAG Manifest 업데이트 완료
  - Obsidian 노트 이동 및 헤더 업데이트 완료
  - 대시보드 업데이트 완료 (Agent/_Dashboard.md)
```
