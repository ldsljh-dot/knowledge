---
description: 수집된 RAG 토픽 현황을 카테고리별로 한눈에 보여줍니다
trigger: /knowledge_dashboard
---

# Knowledge Dashboard Workflow

수집된 RAG 토픽 현황을 카테고리별로 한눈에 보여줍니다.

모든 bash 명령은 프로젝트 루트(`/home/jh/projects/knowledge`)에서 실행합니다.

---

## Step 1: 환경변수 로드

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi
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
```

</tab>
</tabs>

## Step 2: 대시보드 출력

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
DASHBOARD_FILE="$AGENT_DIR/_Dashboard.md"

# 대시보드 생성
python "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" \
  --agent-dir "$AGENT_DIR" \
  --output "$DASHBOARD_FILE"

if [ $? -ne 0 ]; then
  echo "❌ 대시보드 생성 중 오류가 발생했습니다."
  exit 1
fi

# 대시보드 출력
if [ -f "$DASHBOARD_FILE" ]; then
    cat "$DASHBOARD_FILE"
else
    echo "대시보드 파일을 생성할 수 없습니다."
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH/Agent"
$DASHBOARD_FILE = "$AGENT_DIR/_Dashboard.md"

# 대시보드 생성
python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" `
  --agent-dir "$AGENT_DIR" `
  --output "$DASHBOARD_FILE"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 대시보드 생성 중 오류가 발생했습니다."
  exit 1
}

# 대시보드 출력
if (Test-Path "$DASHBOARD_FILE") {
    Get-Content "$DASHBOARD_FILE"
} else {
    Write-Host "대시보드 파일을 생성할 수 없습니다."
}
```

</tab>
</tabs>
