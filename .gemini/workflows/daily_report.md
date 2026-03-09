---
description: Obsidian vault의 일간 활동을 업무·연구 내용 중심으로 정리해 일간 리포트를 작성합니다
trigger: /daily_report
---

# 📅 Daily Report Workflow

Obsidian vault의 특정 날짜 변경사항을 git log와 실제 파일 내용을 기반으로 분석하여
**"어떤 일을 했는가"** 중심의 일간 리포트를 `0-Dashboard/Daily/YYYY-MM-DD.md`에 저장합니다.

> **핵심 원칙**: 파일 이동/생성 같은 파일 시스템 이벤트가 아니라, **어떤 논문을 읽었는지, 어떤 기술을 분석했는지, 어떤 미팅을 했는지** 등 실제 업무·연구 내용을 중심으로 서술합니다.

---

## Phase 1: 환경 설정

### Step 1-1: 환경변수 로드 및 vault 경로 검증

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "AGENT_ROOT: $AGENT_ROOT"
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"

# OBSIDIAN_VAULT_PATH 검증 및 fallback
VAULT_PATH="$OBSIDIAN_VAULT_PATH"

if [ ! -d "$VAULT_PATH" ]; then
  echo "⚠️ OBSIDIAN_VAULT_PATH 경로가 존재하지 않습니다: $VAULT_PATH"
  # 공통 fallback 경로 시도
  for CANDIDATE in "/home/jh/Obsidian" "$HOME/Obsidian" "$HOME/Documents/Obsidian"; do
    if [ -d "$CANDIDATE" ]; then
      echo "→ Fallback 경로 사용: $CANDIDATE"
      VAULT_PATH="$CANDIDATE"
      break
    fi
  done
fi

if [ ! -d "$VAULT_PATH" ]; then
  echo "❌ Vault 경로를 찾을 수 없습니다. .env의 OBSIDIAN_VAULT_PATH를 수정하세요."
  exit 1
fi

echo "✅ Vault 경로: $VAULT_PATH"

# git repo 여부 확인
if [ -d "$VAULT_PATH/.git" ]; then
  GIT_AVAILABLE=true
  echo "✅ Git 저장소 확인됨"
else
  GIT_AVAILABLE=false
  echo "⚠️ Git 저장소가 아닙니다. frontmatter 기반 분석만 수행합니다."
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

Write-Host "AGENT_ROOT: $env:AGENT_ROOT"
Write-Host "OBSIDIAN_VAULT_PATH: $env:OBSIDIAN_VAULT_PATH"

$VAULT_PATH = $env:OBSIDIAN_VAULT_PATH

if (-not (Test-Path $VAULT_PATH)) {
    Write-Host "⚠️ OBSIDIAN_VAULT_PATH 경로가 존재하지 않습니다: $VAULT_PATH"
    foreach ($CANDIDATE in @("$env:USERPROFILE\Obsidian", "C:\Obsidian")) {
        if (Test-Path $CANDIDATE) {
            Write-Host "→ Fallback 경로 사용: $CANDIDATE"
            $VAULT_PATH = $CANDIDATE
            break
        }
    }
}

if (-not (Test-Path $VAULT_PATH)) {
    Write-Host "❌ Vault 경로를 찾을 수 없습니다."
    exit 1
}

Write-Host "✅ Vault 경로: $VAULT_PATH"

if (Test-Path "$VAULT_PATH\.git") {
    $GIT_AVAILABLE = $true
    Write-Host "✅ Git 저장소 확인됨"
} else {
    $GIT_AVAILABLE = $false
    Write-Host "⚠️ Git 저장소가 아닙니다. frontmatter 기반 분석만 수행합니다."
}
```

</tab>
</tabs>

---

## Phase 2: 리포트 날짜 확정 (대화형)

### Step 2-1: 날짜 입력 요청

**[Agent Action]** 사용자에게 질문합니다:

```
📅 리포트 날짜를 입력하세요.
   (기본값: 오늘, Enter로 오늘 날짜 사용)
   형식: YYYY-MM-DD  예) 2026-02-28
```

사용자 입력이 없으면 오늘 날짜를 사용합니다.

### Step 2-2: 날짜 설정 및 기존 리포트 확인

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
REPORT_DATE="${USER_INPUT:-$(date +%Y-%m-%d)}"
REPORT_TIME=$(date +%H:%M)
echo "📅 리포트 대상 날짜: $REPORT_DATE"

DAILY_DIR="$VAULT_PATH/0-Dashboard/Daily"
REPORT_FILE="$DAILY_DIR/${REPORT_DATE}.md"

if [ -f "$REPORT_FILE" ]; then
  echo "⚠️ 이미 해당 날짜의 리포트가 존재합니다:"
  echo "   $REPORT_FILE"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if ($USER_INPUT) { $REPORT_DATE = $USER_INPUT } else { $REPORT_DATE = Get-Date -Format "yyyy-MM-dd" }
$REPORT_TIME = Get-Date -Format "HH:mm"
Write-Host "📅 리포트 대상 날짜: $REPORT_DATE"

$DAILY_DIR = "$VAULT_PATH\0-Dashboard\Daily"
$REPORT_FILE = "$DAILY_DIR\${REPORT_DATE}.md"

if (Test-Path $REPORT_FILE) {
    Write-Host "⚠️ 이미 해당 날짜의 리포트가 존재합니다:"
    Write-Host "   $REPORT_FILE"
}
```

</tab>
</tabs>

기존 리포트가 있을 경우 **[Agent Action]** 사용자에게 확인합니다:

```
❓ 기존 리포트를 덮어쓰시겠습니까? (y = 덮어쓰기 / n = 취소)
```

`n` 입력 시 워크플로우를 종료합니다.

---

## Phase 3: Git 기반 변경사항 수집

### Step 3-1: 해당 날짜 신규 파일 목록 수집

`GIT_AVAILABLE=true`인 경우 실행합니다. 단순 이동(R)은 제외하고 **실제로 새로운 내용이 추가된 파일(A, M)**에 집중합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ "$GIT_AVAILABLE" = "true" ]; then
  echo "=== GIT LOG: 커밋 목록 ==="
  git -C "$VAULT_PATH" log \
    --after="${REPORT_DATE} 00:00:00" \
    --before="${REPORT_DATE} 23:59:59" \
    --name-status \
    --pretty=format:"=== COMMIT %h ===%n%s%n(%ai)" \
    -- "*.md" 2>/dev/null

  echo ""
  echo "=== 신규·수정 파일 목록 (이동 제외) ==="
  git -C "$VAULT_PATH" log \
    --after="${REPORT_DATE} 00:00:00" \
    --before="${REPORT_DATE} 23:59:59" \
    --diff-filter=AM \
    --name-only \
    --pretty=format: \
    -- "*.md" 2>/dev/null | grep -v "^$" | grep -v "0-Dashboard" | sort -u
else
  echo "⏭️ Git 미사용 — frontmatter 기반 분석으로 진행합니다."
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if ($GIT_AVAILABLE) {
    Write-Host "=== GIT LOG: 커밋 목록 ==="
    git -C "$VAULT_PATH" log `
      --after="${REPORT_DATE} 00:00:00" `
      --before="${REPORT_DATE} 23:59:59" `
      --name-status `
      --pretty=format:"=== COMMIT %h ===%n%s%n(%ai)" `
      -- "*.md" 2>$null

    Write-Host ""
    Write-Host "=== GIT STAT: 변경 통계 ==="
    git -C "$VAULT_PATH" log `
      --after="${REPORT_DATE} 00:00:00" `
      --before="${REPORT_DATE} 23:59:59" `
      --shortstat `
      -- "*.md" 2>$null

    Write-Host ""
    Write-Host "=== GIT DIFF: 변경 내용 (최대 600줄) ==="
    git -C "$VAULT_PATH" log `
      --after="${REPORT_DATE} 00:00:00" `
      --before="${REPORT_DATE} 23:59:59" `
      -p --unified=3 `
      --diff-filter=AM `
      -- "*.md" 2>$null | Select-Object -First 600
} else {
    Write-Host "⏭️ Git 미사용 — frontmatter 기반 분석으로 진행합니다."
}
```

</tab>
</tabs>

---

## Phase 4: Frontmatter 교차 확인

git 미추적 파일이나 수동 편집 파일을 보완하기 위해 frontmatter의 날짜 필드를 검색합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
echo "=== FRONTMATTER: created=${REPORT_DATE} ==="
grep -rl "created: ${REPORT_DATE}" "$VAULT_PATH" \
  --include="*.md" 2>/dev/null \
  | grep -v "0-Dashboard" \
  | sort

echo ""
echo "=== FRONTMATTER: updated=${REPORT_DATE} ==="
grep -rl "updated: ${REPORT_DATE}" "$VAULT_PATH" \
  --include="*.md" 2>/dev/null \
  | grep -v "0-Dashboard" \
  | sort
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
Write-Host "=== FRONTMATTER: created=${REPORT_DATE} ==="
Get-ChildItem -Path "$VAULT_PATH" -Recurse -Filter "*.md" |
    Where-Object { $_.FullName -notmatch "0-Dashboard" } |
    Select-String -Pattern "created: $REPORT_DATE" |
    Select-Object -ExpandProperty Path |
    Sort-Object

Write-Host ""
Write-Host "=== FRONTMATTER: updated=${REPORT_DATE} ==="
Get-ChildItem -Path "$VAULT_PATH" -Recurse -Filter "*.md" |
    Where-Object { $_.FullName -notmatch "0-Dashboard" } |
    Select-String -Pattern "updated: $REPORT_DATE" |
    Select-Object -ExpandProperty Path |
    Sort-Object
```

</tab>
</tabs>

---

## Phase 5: 핵심 파일 내용 읽기

### Step 5-1: 신규 파일 내용 읽기

Phase 3에서 수집한 신규·수정 파일 목록 중 **내용이 실질적인 파일**을 읽습니다.

우선순위:
1. `*_조회.md`, `*_Analysis.md` — 직접 작성한 분석·학습 노트 (가장 중요)
2. `*_summary_*.md` — Tavily 수집 요약 (어떤 주제를 리서치했는지 파악)
3. `meetings/*.md` — 미팅 노트
4. `Weekly_Reports/*.md` — 주간 보고서

제외:
- `sources/` 내 개별 웹 소스 파일 (summary만으로 충분)
- 단순 rename된 파일 (내용 변경 없음)
- 파일 수가 많을 경우 각 카테고리별 대표 파일 1~2개만 읽기

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 읽을 파일 예시 (Agent가 위 우선순위로 판단해 선택)
PRIORITY_FILES=$(git -C "$VAULT_PATH" log \
  --after="${REPORT_DATE} 00:00:00" \
  --before="${REPORT_DATE} 23:59:59" \
  --diff-filter=AM \
  --name-only \
  --pretty=format: \
  -- "*.md" 2>/dev/null \
  | grep -v "^$" \
  | grep -v "0-Dashboard" \
  | grep -v "sources/.*[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}\.md" \
  | sort -u)

echo "$PRIORITY_FILES"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
$PRIORITY_FILES = git -C "$VAULT_PATH" log `
  --after="${REPORT_DATE} 00:00:00" `
  --before="${REPORT_DATE} 23:59:59" `
  --diff-filter=AM `
  --name-only `
  --pretty=format: `
  -- "*.md" 2>$null |
  Where-Object { $_ -ne "" -and $_ -notmatch "0-Dashboard" -and $_ -notmatch "sources/.*\d{4}-\d{2}-\d{2}\.md" } |
  Sort-Object -Unique

$PRIORITY_FILES
```

</tab>
</tabs>

**[Agent Action]** 위 목록에서 우선순위에 따라 핵심 파일들을 Read 툴로 읽어 내용을 파악합니다.

---

## Phase 6: 리포트 합성

### Step 6-1: [Agent Action] 업무·연구 내용 중심 리포트 작성

읽은 파일 내용을 바탕으로 아래 원칙과 형식으로 리포트를 작성합니다.

**작성 원칙:**

- **파일 이동·생성 이벤트 위주로 쓰지 않는다** — "Inbox에서 옮겼다", "파일을 생성했다" 같은 서술 금지
- **실제 업무·연구 내용을 매우 구체적으로 서술한다** — "SpecPIM 논문을 읽었다 → 핵심 기여는 X이다", "Xiaoyu Ma와 미팅 → HBF 포지셔닝 논의, 결론은 Y"
- **논문은 제목 + 핵심 기여/내용 요약** 포함 (단순 제목 나열이 아닌, 구조와 핵심 아이디어를 상세히)
- **기술 분석 노트는 어떤 기술을 얼마나 깊게 파악했는지** 서술 (분석한 아키텍처, 메커니즘, 데이터 흐름 등의 디테일한 컨텍스트를 최대한 살려서 반영)
- **미팅 노트는 논의 내용과 결론** 포함
- **[GUARD] 컨텍스트 유지 검증:** 리포트를 생성한 후, 원본 파일의 내용 길이와 생성된 요약을 비교하세요. 만약 원본 컨텍스트가 5줄 이상의 의미 있는 내용을 담고 있는데 요약된 내용이 2줄 이하로 지나치게 축약되었다면, **반드시 원본의 디테일(아키텍처, 핵심 로직, 트레이드오프 등)을 더 포함하여 리포트를 다시 상세하게(Deep Dive 수준으로) 작성**하세요. 지나친 요약으로 인해 중요한 맥락과 지식이 유실되지 않도록 하는 것이 핵심입니다.
- 변경 내용이 전혀 없으면:

```
📭 {REPORT_DATE} 날짜의 변경사항이 없습니다.
   리포트를 생성하지 않습니다.
```

**리포트 형식:**

```markdown
---
created: {REPORT_DATE} {REPORT_TIME}
updated: {REPORT_DATE} {REPORT_TIME}
tags: [daily_note]
type: daily-report
---

# 📅 {REPORT_DATE} 업무 및 활동 로그

## 🏢 업무 — {업무 섹션 제목}
{미팅, 보고서, 기획 등 업무 내용. 논의한 내용과 결론 중심으로 서술}

## 🔬 연구 — {연구 주제}
{어떤 기술/논문을 분석했는지, 핵심 내용은 무엇인지 서술}

## 📄 논문 리서치
{수집·읽은 논문들: 제목, 발표 학회/연도, 핵심 기여 1~3문장}

## 🛠️ 개발 — {개발 내용}
{구현하거나 설계한 내용}

## 💡 오늘의 핵심 인사이트
1. {오늘 활동에서 도출한 핵심 인사이트}

## 🔗 관련 노트
- [[{노트 제목}]]

## 📅 내일 이어갈 작업 제안
1. {오늘 작업의 자연스러운 후속 작업}
```

> 해당 날짜에 업무/연구/논문/개발 중 없는 섹션은 생략합니다.

합성된 리포트를 `REPORT_CONTENT` 변수에 보관합니다.

---

## Phase 6: 리포트 저장

### Step 6-1: 파일 저장

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
mkdir -p "$DAILY_DIR"
cat > "$REPORT_FILE" << 'REPORT_EOF'
{REPORT_CONTENT}
REPORT_EOF

if [ $? -eq 0 ]; then
  echo "✅ 리포트 저장 완료!"
  echo "   📄 $REPORT_FILE"
  echo ""
  echo "--- 저장된 리포트 미리보기 (처음 30줄) ---"
  head -n 30 "$REPORT_FILE"
else
  echo "❌ 파일 저장 중 오류가 발생했습니다."
  exit 1
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
New-Item -ItemType Directory -Force -Path "$DAILY_DIR" | Out-Null
Set-Content -Path "$REPORT_FILE" -Value $REPORT_CONTENT -Encoding UTF8

if ($?) {
    Write-Host "✅ 리포트 저장 완료!"
    Write-Host "   📄 $REPORT_FILE"
    Write-Host ""
    Write-Host "--- 저장된 리포트 미리보기 (처음 30줄) ---"
    Get-Content "$REPORT_FILE" | Select-Object -First 30
} else {
    Write-Host "❌ 파일 저장 중 오류가 발생했습니다."
    exit 1
}
```

</tab>
</tabs>

### Step 6-2: 완료 안내

```
✅ 일간 리포트 생성 완료!

📄 파일 위치: 0-Dashboard/Daily/{REPORT_DATE}.md
🗓️ 대상 날짜: {REPORT_DATE}

Obsidian에서 확인하거나 아래 경로에서 열어보세요:
  {REPORT_FILE}

💡 주간 리포트가 필요하다면 /weekly_report 를 실행하세요.
```

---

## Notes

- **경로 fallback**: `OBSIDIAN_VAULT_PATH`가 존재하지 않으면 `/home/jh/Obsidian` 등 공통 경로를 자동 탐색
- **git 없이도 동작**: vault가 git 저장소가 아닌 경우 frontmatter 날짜 기반 분석만 수행
- **덮어쓰기 확인**: 동일 날짜 리포트가 이미 있으면 사용자 확인 후 진행
- **0-Dashboard 제외**: 리포트 파일 자체의 변경은 분석 대상에서 제외
- **diff 600줄 제한**: 컨텍스트 과부하 방지를 위해 diff 출력을 600줄로 제한
