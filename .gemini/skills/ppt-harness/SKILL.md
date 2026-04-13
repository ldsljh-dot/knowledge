---
name: ppt-harness
description: "PPT 하네스(Rule-Skill-Feedback) 스킬. 원문 데이터를 텍스트 제약·톤·포맷 규칙에 맞춰 PPT 슬라이드 콘텐츠로 변환하는 4단계 파이프라인과 자가 검증 루프를 제공합니다."
---

# PPT Harness (Rule-Skill-Feedback)

Rule-Skill-Feedback 프레임워크를 활용하여 고품질 PPT 슬라이드 콘텐츠를 생성하는 스킬입니다.

## 개요

이 스킬은 4단계 파이프라인과 피드백 루프로 PPT 콘텐츠 품질을 보장합니다:

```
[입력: 원문 데이터]
        ↓
[Phase 1] Structure (구조화)
    → 서론-본론-결론 3막 구조로 슬라이드 목차 추출
    → 출력: slide_outline (JSON)
        ↓
[Phase 2] Copywriting (카피라이팅)
    → 후킹하는 제목 + 간결 불릿 생성
    → 텍스트 제약 강제 적용
    → 출력: enhanced_outline (JSON)
        ↓
[Phase 3] Visualization (시각화 기획)
    → 슬라이드별 시각 자료 기획
    → 출력: outline_with_visuals (JSON)
        ↓
[Phase 4] Scripting (스크립팅)
    → 발표자 스크립트 작성
    → 톤 규칙 적용
    → 출력: complete_slides (JSON)
        ↓
[Phase 5] Feedback (피드백)
    → 4가지 체크리스트 검증
    → 위반 시 자동 재작성 (최대 3회)
    → 출력: final_slides (JSON)
```

---

## Rules (규칙)

하네스는 다음 규칙을 정의합니다. 이 규칙은 4단계 스킬 실행 전반에 적용됩니다.

### 1. 텍스트 제약 (Text Constraints)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `max_bullets_per_slide` | 3 | 슬라이드당 최대 불릿 포인트 수 |
| `max_chars_per_bullet` | 20 | 불릿당 최대 글자 수 (한국어) |
| `max_title_length` | 30 | 제목 최대 글자 수 |

**예시 (통과 vs 실패)**:
```
[통과] "AI는 생각하지 않습니다" (13자) ✓
[통과] "3가지 핵심 요약" (10자) ✓
[실패] "인공지능은 인간의 지능을 모방하고 인간보다 우월한 성능을 보여주는 시스템입니다" (55자) ✗
[실패] ["첫째, ...", "둘째, ...", "셋째, ...", "넷째, ..."] (불릿 4개) ✗
```

### 2. 톤 앤 매너 (Tone and Manner)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `script_style` | `professional_conversational` | 스크립트 스타일: 전문적이지만 친근한 구어체 |
| `script_ending` | `~습니다/~하죠` | 문장 종결 어미 (선택적 사용) |
| `language` | `ko` | 언어 (한국어, 영어 등) |
| `jargon_handling` | `add_brief_analogy_in_parentheses` | 전문 용어 처리 방식 |

**스크립트 예시**:
```
[기본] "이 기술은 데이터 병렬 처리를 획기적으로 개선합니다. 비용 절감이 가능합니다."
[추천] "이 기술은 데이터 병렬 처리를 획기적으로 개선하죠. 비용 절감이 가능합니다."
[용어 비유] "LLM(대규모 언어 모델, 사람 언어 패턴을 학습)은 맥락 이해에 강합니다."
```

### 3. 출력 포맷 (Output Format)

**필수 필드 (required_fields)**:
- `slide_number` — 슬라이드 번호
- `type` — 슬라이드 타입 (아래 `slide_types` 참조)
- `title` — 슬라이드 제목
- `subtitle` — 슬라이드 부제목 (선택)
- `key_points` — 핵심 포인트 배열 (불릿)
- `visual_description` — 시각 자료 묘사
- `speaker_script` — 발표자 스크립트

**슬라이드 타입 (slide_types)**:
| 타입 | 용도 |
|------|------|
| `title` | 표지 슬라이드 |
| `content` | 본문 슬라이드 |
| `toc` | 목차 슬라이드 |
| `section_divider` | 섹션 구분 슬라이드 |
| `conclusion` | 결론/요약 슬라이드 |

### 4. 검증 게이트 (Validation Gates)

| 게이트 | 설명 |
|-------|------|
| `text_length` | 텍스트 길이 제약 위반 검증 |
| `logical_flow` | 슬라이드 간 논리적 연결성 검증 |
| `duplication` | 텍스트 중복 표현 검증 |
| `format_compliance` | 필수 필드 누락 검증 |

---

## Skill 1: Structure (구조화)

서론-본론-결론 구조로 원문 데이터를 슬라이드 목차로 분할합니다.

### 입력

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `raw_content` | string/text/file | 원문 데이터 (텍스트, 마크다운, 또는 파일 경로) |
| `num_slides` | integer (선택) | 생성할 슬라이드 수 (기본값: 추론) |
| `slide_types` | array | 허용 슬라이드 타입 목록 |

### 처리 로직

1. 원문 내용을 분석하여 핵심 섹션 파악
2. 서론(15%) - 본문(70%) - 결론(15%) 비율로 슬라이드 분할
3. 각 섹션별로 슬라이드 타입 분류 (title, content, section_divider, conclusion 등)
4. 슬라이드 번호 부여 및 섹션 레벨 지정

### 출력 형식

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
    "type": "section_divider",
    "title": "PART 1",
    "section": "서론"
  },
  ...
]
```

### 상세 가이드

- **서론 슬라이드**: 도입 배경, 문제 제기, 기대 효과
- **본문 슬라이드**: 핵심 논지, 증거, 사례
- **결론 슬라이드**: 요약, 시사점, 액션 아이템
- **목차 포함**: 서론 앞에 전체 목차 슬라이드(type: toc) 추가 권장

---

## Skill 2: Copywriting (카피라이팅)

후킹하는 제목과 간결한 불릿 포인트를 생성합니다. 텍스트 제약을 엄격하게 적용합니다.

### 입력

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `slide_outline` | array (JSON) | Structure 스킬 출력 |
| `max_title_len` | integer | 제목 최대 글자 수 |
| `max_bullets` | integer | 슬라이드당 최대 불릿 수 |
| `max_chars_bullet` | integer | 불릿당 최대 글자 수 |

### 처리 로직

1. 각 슬라이드 제목을 1줄 카피로 변환 (제목 길이 제약 적용)
2. key_points를 간결한 불릿으로 요약 (불릿 수 및 길이 제약 적용)
3. 자가 점검: 생성 후 즉시 글자 수 확인하고 초과 시 자동 축약

### 제목 카피라이팅 팁

| 원래 제목 | 후킹 제목 예시 |
|-----------|--------------|
| "LLM 하네스 엔지니어링" | "AI 통제의 구조적 비계 설계" |
| "Harness Engineering이란?" | "Rule-Skill-Feedback, 그게 뭡까?" |
| "핵심 구성 요소" | "4가지 필수 요소" |
| "보안 관측 평가" | "안전·관측·평가, 3가지" |

### 불릿 포인트 작성 팁

| 패턴 | 예시 |
|--------|------|
| 명사형 종결 | "데이터 병렬 처리 지원", "자동 튜닝 시스템", "비용 절감 효과" |
| 동사형 (~한다) | "데이터를 분할합니다", "결과를 요약합니다", "모델을 학습합니다" |
| 수사형 (~성) | "높은 확장성", "강력한 성능", "신뢰할 수준" |

### 길이 자가 점검 절차

```
1. 불릿 포인트 초안 작성
2. 글자 수 카운트 (wc -m 또는 내장 카운트)
3. max_chars_per_bullet 초과 시:
   - 단어 축약 (예: "인공지능" → "AI")
   - 구조 단순화 (예: "데이터를 수집하고 분석합니다" → "데이터 수집·분석")
   - 접속사 사용 (예: "~기인" → "기반")
4. 3회 내에 제한 준수
```

---

## Skill 3: Visualization (시각화 기획)

각 슬라이드에 적합한 시각 자료를 기획합니다. PptxGenJS로 구현 가능한 수준의 묘사를 제공합니다.

### 입력

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `enhanced_outline` | array (JSON) | Copywriting 스킬 출력 |

### 처리 로직

1. 각 슬라이드의 내용을 분석하여 최적 시각 자료 타입 결정
2. PptxGenJS 구현 가능한 묘사 작성
3. 레이아웃 제안 (좌-우 분할, 전체 이미지, 중앙 정렬 등)
4. 이미지 생성이 필요한 경우 프롬프트 포함

### 시각 자료 타입

| 타입 | 사용 슬라이드 | PptxGenJS 구현 |
|------|--------------|----------------|
| `graph` | 데이터 비교, 추이 | `pres.addChart()` (BAR, LINE, PIE) |
| `diagram` | 구조, 프로세스 | `pres.addShape()` (RECTANGLE, LINE, OVAL 조합) |
| `image` | 사진, 일러스트 | `slide.addImage()` (file, URL, base64) |
| `icon` | 불릿 포인트 강조 | `slide.addText()` + 이모지 또는 아이콘 문자 |
| `table` | 데이터 비교 테이블 | `pres.addTable()` |
| `infographic` | 복합 정보 시각화 | shape + text 조합 |

### 슬라이드 타입별 추천 시각 자료

| 슬라이드 타입 | 추천 시각 자료 |
|--------------|--------------|
| `title` | 추상 배경, 로고, 브랜딩 요소 |
| `toc` | 번호 목록, 섹션 구분 아이콘 |
| `section_divider` | 섹션 번호 대형 텍스트, 간결 라인 |
| `content` | (불릿 1~3개에 따라 다름) — 아래 매트릭스 참조 |
| `conclusion` | 요약 카드, 체크박스, 아이콘 목록 |

### Content 슬라이드 불릿 수별 추천

| 불릿 수 | 추천 시각 자료 |
|---------|--------------|
| 1개 | 대형 인포그래픽, 풀 스크린 이미지 |
| 2개 | 분할 레이아웃 (좌/우 40:60), 아이콘 쌍 |
| 3개 | 3칸 카드, 그래프 + 캡션, 테이블 |

### visual_description 예시

```
[graph] "본문에 언급된 3가지 기법의 성능 비교 막대 그래프.
        X축: 기법 이름, Y축: 처리 속도(ms). 가장 빠른 기법을 강조 색상으로 표시."

[diagram] "왼쪽에 3단계 프로세스 다이어그램.
        Step 1→2→3 순서대로 화살표로 연결. 각 단계는 둥근 사각형으로 표시.
        오른쪽에 간단 설명 텍스트."

[infographic] "3가지 핵심 장점을 아이콘 + 텍스트 형태로 중앙 배치.
        상단: '📊', '⚡', '🔒' 이모지. 하단: 각각 1줄 설명."
```

---

## Skill 4: Scripting (스크립팅)

각 슬라이드별 발표자 스크립트를 작성합니다. 톤 규칙을 적용합니다.

### 입력

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `outline_with_visuals` | array (JSON) | Visualization 스킬 출력 |
| `script_style` | string | 스크립트 스타일 |
| `script_ending` | string | 문장 종결 어미 |
| `language` | string | 언어 |
| `jargon_handling` | string | 전문 용어 처리 방식 |

### 처리 로직

1. 각 슬라이드의 key_points를 확장하여 서술형 스크립트 작성
2. visual_description 내용을 스크립트에 자연스럽게 통합
3. 스크립트 스타일과 어미 규칙 적용
4. 전문 용어에 괄호 비유 추가

### 분량 기준

- **한국어**: 슬라이드당 150~200자 (1분 발표 분량)
- **영어**: 슬라이드당 100~130 단어 (1분 발표 분량)

### 스크립트 구조 팁

```
[서문] "먼저 이 슬라이드에서는 ~에 대해 설명해드리겠습니다."

[본문] "(불릿 1) ...입니다. (불릿 2) 그리고, ~합니다.
       (불릿 3) 이렇게 ~하죠."

[전문 용어] "RAG(Retrieval-Augmented Generation, 검색 증강 생성)은~"
                또는 "RLHF(Reinforcement Learning from Human Feedback, 인간 피드백 학습)처럼~"

[연결] "다음 슬라이드에서는 ~를 자세히 살펴보겠습니다."
```

### 스크립트 예시 (같은 슬라이드)

```
[구조] Key Points + Visual
[스크립트] "이 슬라이드에서는 핵심 구성 요소 3가지를 살펴보겠습니다.

          첫째, Rules입니다. AI가 벗어날 수 없는 절대적인 가드레일을 설정합니다.
          둘째, Skills입니다. 복잡한 작업을 모듈로 쪼개어 처리합니다.
          셋째, Feedback입니다. 결과물을 스스로 검증하고 개선합니다.

          (시각 자료 참조) 오른쪽 다이어그램에서 3가지 요소가 순환 구조를 이루는 것을 볼 수 있습니다.
          이 하네스가 AI의 자의적 한계를 극복하는 구조적 비계를 제공하죠.

          다음으로, 각 구성 요소의 구체적 사례를 알아보겠습니다."
```

---

## Feedback (피드백)

4가지 체크리스트로 슬라이드 콘텐츠를 검증합니다. 위반 시 자동 재작성합니다.

### 체크리스트

| # | 항목 | 설명 | 검증 방법 | 임계치 |
|---|------|------|----------|--------|
| 1 | text_length | 글자 수 및 불릿 수 제약 준수 | 글자 수 > limit, 불릿 수 > max |
| 2 | logical_flow | 슬라이드 간 논리적 연결성 | Claude 평가 (의미적 판단) |
| 3 | duplication | 텍스트 중복 표현 | n-gram 유사도 ≥ 0.4 |
| 4 | format_compliance | 필수 필드 포함 | 필드 누락 탐지 |

### 검증 절차

1. **text_length**: `validate_slides.py` 스크립트로 결정론적 검증
2. **logical_flow**: Claude가 슬라이드 순서대로 읽으며 연결성 평가
3. **duplication**: `validate_slides.py`의 2-gram Jaccard 유사도 검사
4. **format_compliance**: 필수 필드 존재 여부 확인

### 재작성 루프

```
Step 5-1: 4가지 체크리스트 실행
    ↓
Step 5-2: 위반 항목 있음?
    ├─ YES → 해당 슬라이드만 재작성 → Step 5-1로
    └─ NO → 검증 통과 → Phase 6로 이동

[재작성 최대 시도 횟수] 기본 3회 (harness.json의 max_rewrite_attempts)
```

### validate_slides.py 연동

```bash
python .gemini/skills/ppt-harness/scripts/validate_slides.py \
  --slides "{slides.json_파일_경로}" \
  --harness "harnesses/default.json" \
  --checks "text_length,format_compliance,duplication" \
  --output "json"
```

출력 JSON 예시:
```json
{
  "passed": false,
  "summary": "3/4 checks passed, 2 slides have violations",
  "checks": {
    "text_length": {
      "passed": false,
      "violations": [
        {"slide": 3, "field": "bullets[1]", "actual": 28, "max": 20},
        {"slide": 5, "field": "title", "actual": 35, "max": 30}
      ]
    },
    "format_compliance": {"passed": true, "violations": []},
    "duplication": {"passed": true, "violations": []}
  }
}
```

---

## 하네스 사용법

### 워크플로우에서의 사용

워크플로우 `.gemini/workflows/ppt_harness.md`를 참조하여 단계별로 실행합니다.

### 직접 사용

**Step 1: 하네스 규칙 로드**
```bash
# 기본 하네스
cat .gemini/skills/ppt-harness/harnesses/default.json

# 커스텀 하네스
cat /path/to/custom_harness.json
```

**Step 2~4**: 각 스킬별 지침에 따라 순차 처리

**Step 5**: `validate_slides.py`로 피드백 검증

---

## 의존성

```bash
# Python
rank-bm25          # pip install rank-bm25 (duplication 검증용)
python-dotenv       # pip install python-dotenv (선택)

# Node.js (pptx-generator 연동 시)
pptxgenjs           # npm install -g pptxgenjs
```

---

## 워크플로우 연동

이 스킬은 `.gemini/workflows/ppt_harness.md` 워크플로우에서 호출됩니다:

- Phase 0: 하네스 SKILL.md 로드 및 JSON 규칙 추출
- Phase 1: Structure 스킬 (이 문서 지침 참조)
- Phase 2: Copywriting 스킬
- Phase 3: Visualization 스킬
- Phase 4: Scripting 스킬
- Phase 5: Feedback (validate_slides.py + Claude 평가)
- Phase 6: pptx-generator 연동 (JS 파일 생성 및 PPTX 컴파일)

---

## 주의사항

1. **텍스트 길이는 엄격하게 적용**: 불릿당 20자는 한국어 기준으로, 한 영어 단어와는 다릅니다. 맥락에 따라 조정이 필요할 수 있습니다.
2. **logical_flow는 Claude가 평가**: 결정론적 판단이 어려우므로 워크플로우 단계에서 Claude의 의미적 이해를 활용합니다.
3. **duplication 검증은 2-gram 기반**: 의미적 중복까지 완전히 포착하지 못할 수 있으므로 Claude의 추가 판단과 함께 사용합니다.
4. **필수 필드 누락 시 컴파일 실패**: `pptx-generator`가 기대하는 필드를 제공해야 합니다.
