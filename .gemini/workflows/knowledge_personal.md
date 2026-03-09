---
description: 일정/메모 관리 (SQLite 기반 정확한 개인 데이터) — ZeroClaw/OpenClaw/Claude/Gemini 공유
trigger: /knowledge_personal
---

# Knowledge Personal Workflow

일정(Events)과 메모(Memos)를 SQLite DB로 정확하게 관리합니다.
LLM이 텍스트를 직접 해석하는 대신 스크립트가 정확한 결과를 반환합니다.

**DB 위치**: `$OBSIDIAN_VAULT_PATH/Agent/personal.db` (모든 에이전트 공유)

---

## Prerequisites

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "AGENT_ROOT: $AGENT_ROOT"
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"
echo "DB: $OBSIDIAN_VAULT_PATH/Agent/personal.db"
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
```

</tab>
</tabs>

---

## Phase 1: 동작 선택

사용자에게 질문합니다:

> **"어떤 작업을 하시겠습니까?"**
>
> **일정 관련:**
> 1. 일정 조회 (날짜/기간/키워드)
> 2. 일정 추가
> 3. 일정 수정
> 4. 일정 삭제
>
> **메모 관련:**
> 5. 메모 검색
> 6. 메모 추가
> 7. 메모 수정
> 8. 메모 삭제

사용자의 답변에 따라 Phase 2의 해당 스텝으로 이동합니다.

---

## Phase 2: 실행

### Step 2-1: 일정 조회

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 특정 날짜 조회
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query \
  --date "{날짜, e.g. 2026-03-28}"

# 기간 조회
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query \
  --from "{시작날짜}" --to "{종료날짜}"

# 키워드 검색
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query \
  --keyword "{키워드}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

# 특정 날짜 조회
python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query `
  --date "{날짜}"

# 기간 조회
python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query `
  --from "{시작날짜}" --to "{종료날짜}"
```

</tab>
</tabs>

---

### Step 2-2: 일정 추가

사용자에게 필요 정보를 질문합니다:
- **제목** (필수)
- **시작 일시** (필수, e.g. `2026-03-28T14:00`)
- **종료 일시** (선택)
- **장소** (선택)
- **태그** (선택, e.g. `work`, `meeting`)
- **출처** (zeroclaw/openclaw/user)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" add \
  --title "{제목}" \
  --start "{시작일시}" \
  --end "{종료일시}" \
  --location "{장소}" \
  --tags '["{태그1}","{태그2}"]' \
  --source "{출처}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" add `
  --title "{제목}" `
  --start "{시작일시}" `
  --end "{종료일시}" `
  --location "{장소}" `
  --tags '["{태그1}","{태그2}"]' `
  --source "{출처}"
```

</tab>
</tabs>

---

### Step 2-3: 일정 수정

먼저 수정할 일정을 조회하여 ID를 확인합니다 (Step 2-1 참조).

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" update \
  --id "{ID}" \
  --title "{새_제목}" \
  --start "{새_시작일시}" \
  --location "{새_장소}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" update `
  --id "{ID}" `
  --title "{새_제목}"
```

</tab>
</tabs>

---

### Step 2-4: 일정 삭제

먼저 삭제할 일정을 조회하여 ID를 확인합니다.

> ⚠️ **삭제 전 확인**: 사용자에게 조회 결과를 보여주고 삭제 의사를 재확인합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" delete \
  --id "{ID}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" delete `
  --id "{ID}"
```

</tab>
</tabs>

---

### Step 2-5: 메모 검색

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 키워드 검색
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" search \
  --keyword "{키워드}"

# 태그 검색
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" search \
  --tag "{태그}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" search `
  --keyword "{키워드}"
```

</tab>
</tabs>

---

### Step 2-6: 메모 추가

사용자에게 필요 정보를 질문합니다:
- **제목** (필수)
- **내용** (필수)
- **태그** (선택)
- **출처** (zeroclaw/openclaw/user)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" add \
  --title "{제목}" \
  --content "{내용}" \
  --tags '["{태그1}"]' \
  --source "{출처}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" add `
  --title "{제목}" `
  --content "{내용}" `
  --tags '["{태그1}"]' `
  --source "{출처}"
```

</tab>
</tabs>

---

### Step 2-7: 메모 수정

먼저 수정할 메모를 검색하여 ID를 확인합니다 (Step 2-5 참조).

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" update \
  --id "{ID}" \
  --content "{새_내용}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" update `
  --id "{ID}" `
  --content "{새_내용}"
```

</tab>
</tabs>

---

### Step 2-8: 메모 삭제

> ⚠️ **삭제 전 확인**: 사용자에게 검색 결과를 보여주고 삭제 의사를 재확인합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" delete \
  --id "{ID}"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" delete `
  --id "{ID}"
```

</tab>
</tabs>

---

## Phase 3: 결과 출력

스크립트 출력 결과를 그대로 사용자에게 보여줍니다.

```
✅ 완료!

추가 작업이 필요하시면:
  - 일정/메모 관리: /knowledge_personal
  - 지식 검색: /knowledge_query

```
