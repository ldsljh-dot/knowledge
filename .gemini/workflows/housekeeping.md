---
created: 2026-05-05
updated: 2026-05-05
description: 고아 데이터 정리 및 미편입 지식 탐색/편입을 위한 통합 워크플로우
trigger: /housekeeping
---

# Housekeeping Workflow

Obsidian Vault의 지식 상태를 점검하고 유지보수합니다.
1) **고아 정리(Orphan Cleanup)**: 지워진 노트를 Vault Index와 Mem0에서도 삭제합니다.
2) **미편입 지식 편입(Discovery & Integration)**: 수동으로 생성한 노트 중 Knowledge System에 편입되지 않은 노트를 찾아 인덱싱합니다.

---

## Prerequisites

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:8}..."
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

Write-Host "OBSIDIAN_VAULT_PATH: $env:OBSIDIAN_VAULT_PATH"
if ($env:ANTHROPIC_API_KEY) { Write-Host "ANTHROPIC_API_KEY: $($env:ANTHROPIC_API_KEY.Substring(0,8))...." }
```

</tab>
</tabs>

---

## Phase 1: 고아 정리 (Orphan Cleanup)

### Step 1-1: 현재 상태 확인 (Dry Run)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/sync_clean.py"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT\.gemini\skills\vault-index\scripts\sync_clean.py"
```

</tab>
</tabs>

### Step 1-2: 실제 정리 실행 여부 확인

LLM Agent는 사용자에게 위 dry-run 결과를 요약하여 보여주고, 삭제를 진행할지 묻습니다.
사용자가 동의하면 아래 명령을 실행합니다. (동의하지 않으면 Phase 2로 바로 넘어갑니다.)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/sync_clean.py" --execute
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT\.gemini\skills\vault-index\scripts\sync_clean.py" --execute
```

</tab>
</tabs>

---

## Phase 2: 미편입 지식 탐색 (Discovery & Integration)

### Step 2-1: 미편입 폴더 탐색

Knowledge Engine 시스템을 통하지 않고 Obsidian에 수동으로 생성된 유효한 지식(노트) 폴더들을 찾습니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/sync_clean.py" --discover --json
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT\.gemini\skills\vault-index\scripts\sync_clean.py" --discover --json
```

</tab>
</tabs>

### Step 2-2: 사용자 선택 및 편입 작업

LLM Agent는 위에서 출력된 JSON 목록을 파싱하여 사용자에게 **편입할 폴더를 복수 선택**하도록 제안합니다.
사용자가 편입할 폴더 경로들을 선택하면, **선택된 각 폴더에 대해** 아래 두 스크립트를 순차적으로 실행하여 시스템에 편입합니다.

**선택된 폴더(예: `1-Projects/MyTopic`)마다 다음을 실행하세요:**

*(아래 스크립트에서 `$TOPIC_PATH`를 사용자가 선택한 폴더의 전체 경로(예: `1-Projects/MyTopic`)로 대체합니다.)*

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 1) RAG Manifest 생성
python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" --topic "$(basename "$TOPIC_PATH")" --sources-dir "$OBSIDIAN_VAULT_PATH/$TOPIC_PATH"

# 2) Vault Indexing
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# 1) RAG Manifest 생성
$TopicName = Split-Path $TOPIC_PATH -Leaf
python "$env:AGENT_ROOT\.gemini\skills\rag-retriever\scripts\create_manifest.py" --topic "$TopicName" --sources-dir "$env:OBSIDIAN_VAULT_PATH\$TOPIC_PATH"

# 2) Vault Indexing
python "$env:AGENT_ROOT\.gemini\skills\vault-index\scripts\vault_index.py"
```

</tab>
</tabs>

---

## Phase 3: 결과 요약

모든 작업이 끝나면 최종적으로 다음 사항을 사용자에게 요약해 줍니다:
1. **고아 정리 결과**: Vault Index X개, Mem0 Y개 정리 완료
2. **신규 편입 결과**: 총 Z개의 폴더가 Knowledge System에 편입됨

필요 시 (기존 Mem0 기억 백필이 필요한 경우), `sync_clean.py --backfill`을 추가로 실행할 수 있다고 안내합니다.