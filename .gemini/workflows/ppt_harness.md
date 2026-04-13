---
created: 2026-04-13
updated: 2026-04-13
description: PPT 하네스(Rule-Skill-Feedback)를 활용한 고품질 PPT 생성 워크플로우. 텍스트 제약, 4단계 스킬 파이프라인, 피드백 검증 루프를 통해 PPTX를 생성합니다.
trigger: /ppt_harness
---

# PPT Harness Workflow

> 💡 **OS 실행 규칙**: 현재 시스템의 OS를 감지하여 적절한 셸을 사용하세요.
> - **Linux/macOS**: `bash`를 사용하여 실행합니다.
> - **Windows**: `powershell`을 사용하여 며, 변수 및 명령어 구문을 Windows 환경에 맞게 조정합니다.

이 워크플로우는 Rule-Skill-Feedback 하네스를 활용하여 고품질 PPT를 생성합니다.

---

## Prerequisites

실행 전 다음을 확인하세요:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 환경 변수 로드 및 AGENT_ROOT 설정
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "AGENT_ROOT: $AGENT_ROOT"
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"

# 의존성 패키지 확인
if ! command -v pptxgenjs &> /dev/null; then
  echo "⚠️ pptxgenjs가 설치되지 않았습니다. 설치를 진행합니다..."
  npm install -g pptxgenjs
fi

if ! python -c "import markitdown, rank_bm25" &> /dev/null; then
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
Write-Host "OBSIDIAN_VAULT_PATH: $env:OBSIDIAN_VAULT_PATH"

# 의존성 패키지 확인
if (!(Get-Command pptxgenjs -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️ pptxgenjs가 설치되지 않았습니다. 설치를 진행합니다..."
    npm install -g pptxgenjs
}

try {
    python -c "import markitdown, rank_bm25" *>$null
} catch {
    Write-Host "⚠️ 필수 패키지가 설치되지 않았습니다. 설치를 진행합니다..."
    pip install -r "$env:AGENT_ROOT\requirements.txt"
}
```

</tab>
</tabs>

---

## Phase 0: 환경 설정 및 하네스 로드

### Step 0-1: 하네스 스킬 문서 로드

스킬 상세 지침을 확보합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

cat "$AGENT_ROOT/.gemini/skills/ppt-harness/SKILL.md"
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

Get-Content "$env:AGENT_ROOT\.gemini\skills\ppt-harness\SKILL.md"
```

</tab>
</tabs>

**[Agent Action]** SKILL.md의 각 섹션(Overview, Rules, Skill 1~4, Feedback)을 읽고 파악하세요.

### Step 0-2: 하네스 규칙 로드

사용자가 기본 하네스를 사용할지 커스텀 하네스를 사용할지 선택합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 기본 하네스 로드
HARNESS_PATH="$AGENT_ROOT/.gemini/skills/ppt-harness/harnesses/default.json"

# 커스텀 하네스 경로가 있으면 대체
if [ -n "$1" ]; then
  HARNESS_PATH="$1"
fi

cat "$HARNESS_PATH"
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

# 기본 하네스 로드
$HARNESS_PATH = "$env:AGENT_ROOT\.gemini\skills\ppt-harness\harnesses\default.json"

# 커스텀 하네스 경로가 있으면 대체
if ($args.Count -gt 0) {
    $HARNESS_PATH = $args[0]
}

Get-Content $HARNESS_PATH
```

</tab>
</tabs>

사용자에게 다음과 같이 묻습니다:

> **"사용할 하네스를 선택하세요:"**
> 1. 기본 하네스 (`ppt-harness/harnesses/default.json`) — Enter로 사용
> 2. 커스텀 하네스 — JSON 파일 경로 입력

**[Agent Action]** 하네스 JSON을 파싱하여 다음 변수를 추출하세요:

| 변수 | JSON 경로 | 설명 |
|------|-----------|------|
| `{MAX_BULLETS}` | `rules.text_constraints.max_bullets_per_slide` | 슬라이드당 최대 불릿 수 (기본: 3) |
| `{MAX_CHARS_BULLET}` | `rules.text_constraints.max_chars_per_bullet` | 불릿당 최대 글자 수 (기본: 20) |
| `{MAX_TITLE_LEN}` | `rules.text_constraints.max_title_length` | 제목 최대 글자 수 (기본: 30) |
| `{SCRIPT_STYLE}` | `rules.tone_and_manner.script_style` | 스크립트 스타일 |
| `{SCRIPT_ENDING}` | `rules.tone_and_manner.script_ending` | 문장 종결 어미 |
| `{LANGUAGE}` | `rules.tone_and_manner.language` | 언어 (기본: ko) |
| `{REQUIRED_FIELDS}` | `rules.output_format.required_fields` | 필수 필드 목록 |
| `{SLIDE_TYPES}` | `rules.output_format.slide_types` | 슬라이드 타입 목록 |
| `{MAX_REWRITE}` | `feedback.max_rewrite_attempts` | 최대 재작성 횟수 (기본: 3) |

### Step 0-3: 사용자 입력 수집

사용자에게 PPT 생성에 필요한 정보를 입력받습니다:

> **"PPT 생성을 시작합니다. 다음 정보를 입력해주세요:"**

1. **주제** (필수): PPT 주제
   예: "AI 하네스 엔지니어링", "CXL 메모리 풀링"

2. **원문 데이터** (필수): 슬라이드 콘텐츠가 될 자료
   - 직접 텍스트 입력
   - 파일 경로 (마크다운, 텍스트 파일)

3. **청중** (선택): 발표 대상 청중
   예: "기술 팀", "경영진팀", "일반 전문가" (기본값 사용하려면 Enter)

4. **슬라이드 수** (선택): 생성할 슬라이드 수
   예: "12" 또는 Enter로 자동 추론 (기본값)

입력받은 값을 저장합니다:
- `{TOPIC}` — 주제
- `{RAW_CONTENT}` — 원문 데이터 (파일 경로면 내용을 읽기)
- `{AUDIENCE}` — 청중
- `{NUM_SLIDES}` — 슬라이드 수

---

## Phase 1: Structure Skill (구조화)

원문 데이터를 서론-본론-결론 구조로 슬라이드 목차를 추출합니다.

### Step 1-1: [Agent Action] 슬라이드 목차 추출

**[Agent Action]** SKILL.md의 "Skill 1: Structure" 지침에 따라 슬라이드 목차를 추출하세요.

**입력**:
- 원문 데이터: `{RAW_CONTENT}`
- 슬라이드 수: `{NUM_SLIDES}`
- 슬라이드 타입 목록: `{SLIDE_TYPES}`

**처리 방법**:
1. 원문을 분석하여 핵심 섹션 파악
2. 서론(15%) - 본문(70%) - 결론(15%) 비율로 슬라이드 분할
3. 각 섹션별로 슬라이드 타입 분류 (`{SLIDE_TYPES}` 중에서 선택)
4. 슬라이드 번호 부여 및 섹션 레벨 지정

**출력 형식** (JSON):

```json
[
  {
    "slide_number": 1,
    "type": "title",
    "title": "...",
    "subtitle": "...",
    "key_points": [],
    "section": "서론"
  },
  {
    "slide_number": 2,
    "type": "toc",
    "title": "Agenda",
    "sections": [...],
    "section": "서론"
  },
  ...
]
```

가이드라인:
- 목차(TOC) 슬라이드를 첫 번호 뒤에 포함 권장
- 각 섹션 시작 전에 `section_divider` 추가 권장
- 서론: 도입 배경, 문제 제기, 기대 효과
- 본문: 핵심 논지, 증거, 사례
- 결론: 요약, 시사점, 액션 아이템

출력을 `{SLIDE_OUTLINE}` 변수에 저장하세요.

---

## Phase 2: Copywriting Skill (카피라이팅)

후킹하는 제목과 간결한 불릿 포인트를 생성합니다. 텍스트 제약을 엄격하게 적용합니다.

### Step 2-1: [Agent Action] 후킹 제목 + 간결 불릿 생성

**[Agent Action]** SKILL.md의 "Skill 2: Copywriting" 지침에 따라 슬라이드 목차를 후킹 카피와 간결 불릿으로 변환하세요.

**입력**:
- 슬라이드 목차: `{SLIDE_OUTLINE}`
- 텍스트 제약: `max_title_len={MAX_TITLE_LEN}`, `max_bullets={MAX_BULLETS}`, `max_chars_bullet={MAX_CHARS_BULLET}`

**처리 방법**:
1. 각 슬라이드 제목을 1줄 카피로 변환 (길이 제약 적용)
2. key_points를 간결한 불릿으로 요약 (수 및 길이 제약 적용)
3. 자가 점검: 생성 후 즉시 글자 수 확인하고 초과 시 자동 축약

**텍스트 제약 (절대 위반 금지)**:
- 제목 길이 ≤ `{MAX_TITLE_LEN}`자
- 불릿 포인트 수 ≤ `{MAX_BULLETS}`개
- 불릿당 길이 ≤ `{MAX_CHARS_BULLET}`자

가이드라인:
- 불릿은 명사형 종결(~것, ~역할) 또는 동사형(~한다, ~지원)으로 통일
- 제목은 의문형이나 도발형으로 후킹
- 자가 점검: 글자 수 초과 시 3회 내에 제한 준수

출력을 `{ENHANCED_OUTLINE}` 변수에 저장하세요.

---

## Phase 3: Visualization Skill (시각화 기획)

각 슬라이드에 적합한 시각 자료를 기획합니다.

### Step 3-1: [Agent Action] 시각 자료 기획

**[Agent Action]** SKILL.md의 "Skill 3: Visualization" 지침에 따라 슬라이드별 시각 자료를 기획하세요.

**입력**:
- 후킹된 목차: `{ENHANCED_OUTLINE}`

**처리 방법**:
1. 각 슬라이드의 내용을 분석하여 최적 시각 자료 타입 결정
2. PptxGenJS 구현 가능한 묘사 작성
3. 레이아웃 제안 (좌-우 분할, 전체 이미지, 중앙 정렬 등)
4. 이미지 생성이 필요한 경우 프롬프트 포함

시각 자료 타입 예시:
- `graph` — 막대 그래프 (BAR, LINE, PIE)
- `diagram` — 구조/프로세스 다이어그램
- `image` — 사진, 일러스트
- `icon` — 불릿 포인트 강조 아이콘
- `table` — 데이터 비교 테이블
- `infographic` — 복합 정보 시각화

가이드라인:
- Content 슬라이드: 불릿 수에 따라 다름 (1개=인포그래픽, 2개=분할 레이아웃, 3개=카드)
- 각 시각 자료는 "시각 자료가 ~를 보여줍니다" 형태로 스크립트에 통합

출력을 `{OUTLINE_WITH_VISUALS}` 변수에 저장하세요.

---

## Phase 4: Scripting Skill (스크립팅)

각 슬라이드별 발표자 스크립트를 작성합니다.

### Step 4-1: [Agent Action] 발표자 스크립트 작성

**[Agent Action]** SKILL.md의 "Skill 4: Scripting" 지침에 따라 발표자 스크립트를 작성하세요.

**입력**:
- 시각화된 목차: `{OUTLINE_WITH_VISUALS}`
- 톤 규칙: `script_style={SCRIPT_STYLE}`, `script_ending={SCRIPT_ENDING}`, `language={LANGUAGE}`

**처리 방법**:
1. 각 슬라이드의 key_points를 확장하여 서술형 스크립트 작성
2. visual_description 내용을 스크립트에 자연스럽게 통합
3. 스크립트 스타일과 어미 규칙 적용
4. 전문 용어에 괄호 비유 추가

**톤 규칙 (절대 위반 금지)**:
- 스크립트 스타일: `{SCRIPT_STYLE}`
- 문장 종결: `{SCRIPT_ENDING}` 사용 (선택적 활용)
- 언어: `{LANGUAGE}` (한국어)
- 전문 용어: 괄호 안에 짧은 비유 추가
- 분량: 슬라이드당 약 150~200자 (1분 발표)

가이드라인:
- 서문: "먼저 이 슬라이드에서는 ~에 대해 설명해드리겠습니다."
- 본문: "(불릿 1) ...입니다. (불릿 2) 그리고, ~합니다."
- 전문 용어: "RAG(대규모 언어 모델, 사람 언어 패턴을 학습)은~"
- 연결: "다음 슬라이드에서는 ~를 자세히 살펴보겠습니다."

출력을 `{COMPLETE_SLIDES}` 변수에 저장하세요.

---

## Phase 5: Feedback / Validation Loop

4가지 체크리스트로 슬라이드를 검증합니다. 위반 시 자동 재작성합니다.

### Step 5-1: 슬라이드 JSON 저장

`{COMPLETE_SLIDES}`를 임시 파일로 저장합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 임시 슬라이드 파일 생성
mkdir -p "$AGENT_ROOT/.gemini/skills/ppt-harness/temp"
echo "$SLIDES_JSON" > "$AGENT_ROOT/.gemini/skills/ppt-harness/temp/slides.json"

echo "슬라이드 파일 저장 완료: $AGENT_ROOT/.gemini/skills/ppt-harness/temp/slides.json"
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

# 임시 슬라이드 파일 생성
New-Item -ItemType Directory -Force -Path "$env:AGENT_ROOT\.gemini\skills\ppt-harness\temp" | Out-Null
$SLIDES_JSON | Out-File -FilePath "$env:AGENT_ROOT\.gemini\skills\ppt-harness\temp\slides.json" -Encoding UTF8

Write-Host "슬라이드 파일 저장 완료: $env:AGENT_ROOT\.gemini\skills\ppt-harness\temp\slides.json"
```

</tab>
</tabs>

### Step 5-2: 결정론적 검증 (validate_slides.py)

`validate_slides.py` 스크립트로 text_length, format_compliance, duplication을 검증합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 검증 실행
python3 "$AGENT_ROOT/.gemini/skills/ppt-harness/scripts/validate_slides.py" \
  --slides "$AGENT_ROOT/.gemini/skills/ppt-harness/temp/slides.json" \
  --harness "$AGENT_ROOT/.gemini/skills/ppt-harness/harnesses/default.json" \
  --checks "text_length,format_compliance,duplication" \
  --output "json"

if [ $? -ne 0 ]; then
  echo "❌ 검증 중 오류가 발생했습니다."
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

# 검증 실행
python "$env:AGENT_ROOT\.gemini\skills\ppt-harness\scripts\validate_slides.py" `
  --slides "$env:AGENT_ROOT\.gemini\skills\ppt-harness\temp\slides.json" `
  --harness "$env:AGENT_ROOT\.gemini\skills\ppt-harness\harnesses\default.json" `
  --checks "text_length,format_compliance,duplication" `
  --output "json"

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ 검증 중 오류가 발생했습니다."
  exit 1
}
```

</tab>
</tabs>

### Step 5-3: [Agent Action] 검증 결과 평가 및 재작성 루프

**[Agent Action]** validate_slides.py의 출력(JSON)을 분석하고 위반 항목을 평가하세요.

**검증 결과 분석**:
1. **text_length 위반**: 불릿 수 초과, 불릿 길이 초과, 제목 길이 초과
2. **format_compliance 위반**: 필수 필드 누락
3. **duplication 위반**: 2-gram 유사도 ≥ 0.4인 슬라이드

**Rewrite 루프**:
```
ATTEMPT = 1
MAX_REWRITE = {MAX_REWRITE}

while ATTEMPT <= MAX_REWRITE:
    if any(violations exist):
        실패한 항목만 재작성 → Step 5-1로 저장 → Step 5-2로 재검증
        ATTEMPT += 1
    else:
        루프 탈출 → Phase 6로 이동
```

가이드라인:
- **text_length 실패**: 글자 수를 줄이세요 (축약, 구조 단순화, 접속사 사용)
- **format_compliance 실패**: 누락된 필드를 추가하세요
- **duplication 실패**: 중복 표현을 다른 단어로 교체하거나 내용을 다르게 서술하세요
- **logical_flow 평가**: 스크립트가 이전/다음 슬라이드와 매끄럽게 연결되는지 확인

모든 검증 통과 시 `{FINAL_SLIDES}` 변수에 저장하고 Phase 6으로 이동합니다.

---

## Phase 6: PPTX Generation (pptx-generator 연동)

검증된 슬라이드를 PptxGenJS로 PPTX 파일로 컴파일합니다.

### Step 6-1: pptx-generator 스킬 문서 로드

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

cat "$AGENT_ROOT/.agents/skills/pptx-generator/SKILL.md"
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

Get-Content "$env:AGENT_ROOT\.agents\skills\pptx-generator\SKILL.md"
```

</tab>
</tabs>

### Step 6-2: [Agent Action] 디자인 결정

**[Agent Action]** pptx-generator SKILL.md의 "Step 2: Color Palette & Fonts"와 "Step 3: Select Design Style"에 따라 디자인을 결정하세요.

**주제와 청중 고려**:
- 주제: `{TOPIC}`
- 청중: `{AUDIENCE}`

**결정 사항**:
1. 컬러 팔레트 (SKILL.md의 Color Palette Reference 참조)
2. 폰트 페어링 (SKILL.md의 Font Reference 참조)
3. 디자인 스타일 (Sharp/Soft/Rounded/Pill 중 하나)

출력으로 `{THEME}` 객체를 구성 (primary, secondary, accent, light, bg 예시).

### Step 6-3: [Agent Action] 슬라이드 JS 파일 생성

**[Agent Action]** pptx-generator SKILL.md의 "Step 5: Generate Slide JS Files"에 따라 `{FINAL_SLIDES}` 기반으로 JS 슬라이드 파일을 생성하세요.

**디렉토리 구조**:
```
slides/
├── slide-01.js
├── slide-02.js
├── ...
├── imgs/
└── output/
```

**각 JS 파일 포맷** (SKILL.md의 "Slide Output Format" 참조):
```javascript
// slide-01.js
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: '...',
  index: 1,
  title: '...',
  subtitle: '...',
  key_points: [...],
  visual_type: '...',
  speaker_script: '...'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  // Theme Object Contract 사용: primary, secondary, accent, light, bg
  // Page Number Badge: Cover 제외하고 모든 슬라이드에 x: 9.3", y: 5.1" 배치
  // 텍스트 제약 준수: bullets ≤ 3개, 각 불릿 ≤ 20자, 제목 ≤ 30자

  return slide;
}

if (require.main === module) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  const theme = { /* {THEME} */ };
  createSlide(pres, theme);
  pres.writeFile({ fileName: "slide-01-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
```

**주의사항**:
- 하네스 텍스트 제약을 JS 코드에도 반영하세요
- `{FINAL_SLIDES}`의 각 슬라이드 데이터를 `slideConfig` 객체에 반영
- 불릿 텍스트 길이를 `wc -m`으로 확인하거나 Claude가 카운트하세요

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 슬라이드 디렉토리 생성
mkdir -p slides/imgs slides/output

echo "슬라이드 JS 파일을 slides/ 디렉토리에 생성하세요."
echo "디렉토리 구조: slides/"
echo "  - slide-01.js, slide-02.js, ..."
echo "  - imgs/"
echo "  - output/"
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

# 슬라이드 디렉토리 생성
New-Item -ItemType Directory -Force -Path "slides\imgs" | Out-Null
New-Item -ItemType Directory -Force -Path "slides\output" | Out-Null

Write-Host "슬라이드 JS 파일을 slides\ 디렉토리에 생성하세요."
Write-Host "디렉토리 구조: slides\"
Write-Host "  - slide-01.js, slide-02.js, ..."
Write-Host "  - imgs\"
Write-Host "  - output\"
```

</tab>
</tabs>

### Step 6-4: compile.js 생성 및 PPTX 컴파일

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# compile.js 생성 (pptx-generator SKILL.md 참조)
cat << 'EOF' > slides/compile.js
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = 'PPT Harness';
pres.title = '$(echo "$TOPIC" | sed 's/"/\\"/g')';

const theme = {
  primary: "0a0a0a",
  secondary: "404040",
  accent: "0070F3",
  light: "D4AF37",
  bg: "f5f5f5"
};

// 모든 슬라이드 모듈 로드
const slideCount = ${NUM_SLIDES:-12};
for (let i = 1; i <= slideCount; i++) {
  const num = String(i).padStart(2, '0');
  try {
    const slideModule = require(\`./slide-\${num}.js\`);
    slideModule.createSlide(pres, theme);
  } catch (e) {
    console.error(\`Failed to load slide-\${num}.js: \${e.message}\`);
  }
}

pres.writeFile({ fileName: './output/presentation.pptx' });
console.log('PPTX compilation complete: ./output/presentation.pptx');
EOF

# 컴파일 실행
cd slides && node compile.js

if [ $? -ne 0 ]; then
  echo "❌ PPTX 컴파일 중 오류가 발생했습니다."
  exit 1
fi

echo "✅ PPTX 생성 완료: slides/output/presentation.pptx"
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

$slideCount = if ($NUM_SLIDES) { $NUM_SLIDES } else { 12 }
$topicEscaped = $TOPIC -replace '"', '\"'

# compile.js 생성
@'
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = 'PPT Harness';
pres.title = '" + $topicEscaped + "';

const theme = {
  primary: "0a0a0a",
  secondary: "404040",
  accent: "0070F3",
  light: "D4AF37",
  bg: "f5f5f5"
};

// 모든 슬라이드 모듈 로드
const slideCount = ' + $slideCount + @';
for (let i = 1; i <= slideCount; i++) {
  const num = String(i).padStart(2, '0');
  try {
    const slideModule = require(`./slide-${num}.js`);
    slideModule.createSlide(pres, theme);
  } catch (e) {
    console.error(`Failed to load slide-${num}.js: ${e.message}`);
  }
}

pres.writeFile({ fileName: './output/presentation.pptx' });
console.log('PPTX compilation complete: ./output/presentation.pptx');
'@ | Out-File -FilePath "slides\compile.js" -Encoding UTF8

# 컴파일 실행
cd slides; node compile.js

if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ PPTX 컴파일 중 오류가 발생했습니다."
  exit 1
}

Write-Host "✅ PPTX 생성 완료: slides\output\presentation.pptx"
```

</tab>
</tabs>

### Step 6-5: QA (markitdown 검증)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi

# markitdown으로 텍스트 추출
python -m markitdown slides/output/presentation.pptx

# placeholder 텍스트 검증
python -m markitdown slides/output/presentation.pptx | grep -iE "xxxx|lorem|ipsum|placeholder|this.*(page|slide).*layout"

if [ $? -eq 0 ]; then
  echo "⚠️ placeholder 텍스트가 발견되었습니다. 확인이 필요합니다."
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

# markitdown으로 텍스트 추출
python -m markitdown slides\output\presentation.pptx

# placeholder 텍스트 검증
python -m markitdown slides\output\presentation.pptx | Select-String -Pattern "xxxx|lorem|ipsum|placeholder|this.*(page|slide).*layout" -CaseSensitive

if ($?) {
    Write-Host "⚠️ placeholder 텍스트가 발견되었습니다. 확인이 필요합니다."
}
```

</tab>
</tabs>

---

## Phase 7: 최종 검증 및 완료

### Step 7-1: [Agent Action] 최종 검증

**[Agent Action]** markitdown으로 추출한 텍스트에 대해 하네스 규칙 최종 검증:

1. 각 슬라이드의 불릿 수가 `{MAX_BULLETS}`개 이하인지 확인
2. 각 불릿 텍스트가 `{MAX_CHARS_BULLET}`자 이하인지 확인
3. 제목이 `{MAX_TITLE_LEN}`자 이하인지 확인
4. 페이지 번호가 Cover를 제외한 모든 슬라이드에 있는지 확인

위반 항목이 있으면 해당 slide JS 파일을 수정 후 `node compile.js`로 재컴파일하세요.

### Step 7-2: 완료 메시지

```
✅ PPT 생성 완료!

📊 하네스 규칙 준수 현황:
   - 텍스트 제약 (불릿 {MAX_BULLETS}개/{MAX_CHARS_BULLET}자, 제목 {MAX_TITLE_LEN}자): ✅
   - 톤 앤 매너 ({SCRIPT_STYLE}, {SCRIPT_ENDING}): ✅
   - 필수 필드 ({REQUIRED_FIELDS}): ✅
   - 피드백 체크리스트 (4/4 통과): ✅

📁 생성된 파일:
   - PPTX: slides/output/presentation.pptx
   - 슬라이드 JS: slides/slide-01.js ~ slide-{N}.js
   - 컴파일 스크립트: slides/compile.js
   - 하네스 설정: harnesses/default.json (또는 커스텀)

💡 PPT 내용을 수정하려면 슬라이드 JS 파일을 편집 후 `cd slides && node compile.js` 를 실행하세요.
💡 다른 규칙으로 재생성하려면 커스텀 하네스 JSON 파일을 준비하고 /ppt_harness 를 다시 실행하세요.
```

---

## Notes

- **하네스 JSON**: `harnesses/default.json`에 규칙 정의가 저장되어 있습니다.
- **커스텀 하네스**: Step 0-2에서 파일 경로를 직접 입력하여 사용 가능합니다.
- **검증 스크립트**: `scripts/validate_slides.py`가 text_length, format_compliance, duplication을 결정론적으로 검증합니다.
- **pptx-generator 연동**: Phase 6에서 기존 pptx-generator 스킬을 재사용하여 PPTX를 컴파일합니다.
- **의존성**:
  - `pptxgenjs` — PPTX 생성
  - `markitdown` — QA 검증
  - `rank-bm25` — duplication 검증
