---
description: 수집된 RAG 토픽의 sources/manifest/노트를 선택적으로 삭제합니다
trigger: /knowledge_rm
---

# Knowledge Remove Workflow

수집된 지식(sources, RAG manifest, Obsidian 노트)을 토픽 단위로 삭제합니다.

모든 bash 명령은 프로젝트 루트(`/home/jh/projects/knowledge`)에서 실행합니다.

---

## Phase 1: 삭제 가능한 토픽 목록 표시

### Step 1-1: 환경변수 로드 및 목록 출력

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"

python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/list_topics.py" \
  --agent-dir "$AGENT_DIR"
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

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/list_topics.py" `
  --agent-dir "$AGENT_DIR"
```

</tab>
</tabs>

---

### Step 1-2: 삭제 대상 선택

사용자에게 질문합니다:

> **"어떤 토픽을 삭제하시겠습니까?**
> 식별자(`Category/SafeTopic`)를 입력하세요. 쉼표로 구분하면 복수 선택 가능합니다."

| 입력 예시 | 처리 |
|-----------|------|
| `Security/동형암호기술` | 해당 토픽 단건 삭제 |
| `AI_Study/MemoryLLM_Research, DB_Research/PolarStore_Research` | 복수 토픽 삭제 |
| `AI_Study` | 해당 카테고리 전체 삭제 |

---

## Phase 2: 삭제 범위 확인 및 사용자 확인

### Step 2-1: 삭제될 항목 미리보기

선택한 토픽에 대해 실제 삭제될 항목을 나열합니다:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" \
  --agent-dir "$OBSIDIAN_VAULT_PATH/Agent" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --targets "{선택한_식별자_목록}" \
  --preview
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" `
  --agent-dir "$env:OBSIDIAN_VAULT_PATH/Agent" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --targets "{선택한_식별자_목록}" `
  --preview
```

</tab>
</tabs>

### Step 2-2: 삭제 전 최종 확인

사용자에게 질문합니다:

> **"위 항목을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.**
> `y` 입력 시 삭제 진행 / `n` 입력 시 취소"

`n` 또는 입력 없으면 → 취소 메시지 출력 후 종료

---

## Phase 3: 삭제 실행

### Step 3-1: sources 및 RAG manifest 삭제

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" \
  --agent-dir "$OBSIDIAN_VAULT_PATH/Agent" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --targets "{선택한_식별자_목록}" \
  --delete
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" `
  --agent-dir "$env:OBSIDIAN_VAULT_PATH/Agent" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --targets "{선택한_식별자_목록}" `
  --delete
```

</tab>
</tabs>

### Step 3-2: 관련 Obsidian 노트 삭제 (선택)

삭제 후 사용자에게 추가로 질문합니다:

> **"관련 Obsidian 노트도 삭제하시겠습니까?**
> 토픽명을 포함하는 `.md` 파일을 검색합니다. (`y` / `n`)"

`y` 입력 시:

#### 1. 노트 검색 (Preview)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" \
  --agent-dir "$OBSIDIAN_VAULT_PATH/Agent" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --targets "{선택한_식별자_목록}" \
  --find-notes \
  --preview
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" `
  --agent-dir "$env:OBSIDIAN_VAULT_PATH/Agent" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --targets "{선택한_식별자_목록}" `
  --find-notes `
  --preview
```

</tab>
</tabs>

#### 2. 사용자 확인 및 삭제

사용자가 다시 한 번 확인(`y`)하면:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" \
  --agent-dir "$OBSIDIAN_VAULT_PATH/Agent" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --targets "{선택한_식별자_목록}" \
  --delete-notes
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/delete_knowledge.py" `
  --agent-dir "$env:OBSIDIAN_VAULT_PATH/Agent" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --targets "{선택한_식별자_목록}" `
  --delete-notes
```

</tab>
</tabs>

---

## Phase 4: 완료 메시지

```
✅ 삭제 완료!

🗑  삭제된 항목:
  - Agent/{Category}/{Topic}/sources/
  - Agent/{Category}/{Topic}/rag/

💡 같은 주제를 다시 수집하려면:
   /knowledge_tutor → '{topic}' 입력

💡 현재 남은 토픽 목록:
   /knowledge_dashboard
```
