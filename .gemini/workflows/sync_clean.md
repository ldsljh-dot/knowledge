---
created: 2026-05-05
updated: 2026-05-05
description: Obsidian ↔ Vault Index ↔ Mem0 3계층 동기화 정리 워크플로우
trigger: /sync_clean
---

# Sync Clean Workflow

> ⚠️ **Note**: 이 워크플로우는 `/housekeeping` 으로 통합되었습니다. 새로운 기능(미편입 지식 탐색 등)을 사용하려면 `/housekeeping` 워크플로우를 사용하세요.

Obsidian Vault을 기준(Source of Truth)으로 Vault Index와 Mem0의 고아 데이터를 정리합니다.

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
if ($env:ANTHROPIC_API_KEY) { Write-Host "ANTHROPIC_API_KEY: $($env:ANTHROPIC_API_KEY.Substring(0,8))..." }
```

</tab>
</tabs>

---

## Step 1: dry-run으로 현재 상태 확인

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

dry-run 결과를 사용자에게 표시합니다:

> **"🔍 3계층 동기화 분석 결과:**
>
> - Obsidian 토픽 폴더: X개
> - Vault Index orphan: Y개
> - Mem0 orphan: Z개
> - Mem0 추적불가: W개
>
> **실제 삭제를 실행하시겠습니까?** (yes/no)"

---

## Step 2: 사용자 확인 후 실행

사용자가 `yes`를 입력하면:

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

사용자가 `no`를 입력하면 종료합니다.

---

## Step 3: 백필 (선택)

기존 Mem0 기억에 `obsidian_path` 메타데이터가 없는 경우, 백필을 제안합니다:

> **"기존 Mem0 기억에 obsidian_path를 보강하시겠습니까? (yes/no)"**

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/sync_clean.py" --backfill
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT\.gemini\skills\vault-index\scripts\sync_clean.py" --backfill
```

</tab>
</tabs>

---

## 완료 메시지

```
✅ 3계층 동기화 완료!

  📊 처리 결과:
    - Vault Index orphan 제거: X개
    - Mem0 orphan 제거: Y개
    - Mem0 추적불가 (스킵): Z개
    - obsidian_path 백필: W건

  💡 정기적으로 /sync_clean을 실행하여 일관성을 유지하세요.
```
