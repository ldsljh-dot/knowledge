---
created: 2026-03-10
updated: 2026-03-10
description: 세미나 중 질문/의견을 실시간으로 캡처하고 RAG로 맥락을 보강하여 Obsidian에 저장하는 Hybrid 워크플로우
trigger: /myseminar
---
created: 2026-03-10
updated: 2026-03-10

# 🎙️ My Seminar Q&A Capture Workflow

> 💡 **OS 실행 규칙**: 현재 시스템의 OS를 감지하여 적절한 셸을 사용하세요.
> - **Linux/macOS**: `bash`를 사용하여 실행합니다.
> - **Windows**: `powershell`을 사용하여 실행하며, 변수 및 명령어 구문을 Windows 환경에 맞게 조정합니다.

세미나 중 발생하는 질문과 의견을 실시간으로 캡처합니다.
입력할 때마다 기존 RAG 지식으로 맥락을 보강하고, Obsidian에 즉시 저장합니다.
세션 종료 시 미답 질문 목록과 후속 연구 제안을 생성합니다.

---
created: 2026-03-10
updated: 2026-03-10

## Phase 1: 환경 설정 및 세미나 정보 입력

### Step 1-1: 환경 점검

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "AGENT_ROOT: $AGENT_ROOT"
echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"

python3 -c "import rank_bm25" 2>/dev/null || { echo "📦 Installing dependencies..."; pip install -r "$AGENT_ROOT/requirements.txt"; }
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

try { python -c "import rank_bm25" *>$null } catch {
    Write-Host "📦 Installing dependencies..."
    pip install -r "$env:AGENT_ROOT\requirements.txt"
}
```

</tab>
</tabs>

### Step 1-2: 세미나 정보 입력 (대화형)

사용자에게 아래 정보를 순서대로 질문합니다:

1. **"세미나 주제(Topic)는 무엇인가요?"**
   예: `PIM architecture overview`, `NVBit memory tracing`
2. **"발표자(선택, 엔터로 건너뜀)?"**
   예: `홍길동`, `Jane Smith`

사용자의 답변을 기반으로 `{TOPIC}`과 `{SPEAKER}` 변수를 확정합니다.
저장될 카테고리(`{CATEGORY}`) 변수는 고정값인 `Inbox`로 설정합니다.

---
created: 2026-03-10
updated: 2026-03-10

## Phase 2: RAG 지식 베이스 확인

### Step 2-1: 기존 RAG 존재 여부 확인

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi

TOPIC="{TOPIC}"
CATEGORY="{CATEGORY}"
SAFE_TOPIC=$(echo "$TOPIC" | tr ' /' '__')
SAFE_CATEGORY=$(echo "$CATEGORY" | tr ' /' '__')
AGENT_DIR="$OBSIDIAN_VAULT_PATH"
RAG_MANIFEST="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag/manifest.json"
SOURCE_DIR="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

if [ -f "$RAG_MANIFEST" ]; then
    echo "✅ RAG 존재: $SAFE_CATEGORY/$SAFE_TOPIC"
    python3 -c "
import json
m = json.load(open('$RAG_MANIFEST'))
print(f'  📄 파일 수: {m.get(\"file_count\", 0)}개')
print(f'  📦 크기: {int(m.get(\"total_bytes\",0)/1024)} KB')
print(f'  🕐 최종 업데이트: {m.get(\"updated\",\"\")[:10]}')
"
else
    echo "❌ RAG 없음. 세미나 주제에 대한 사전 지식이 없습니다."
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

$TOPIC = "{TOPIC}"
$CATEGORY = "{CATEGORY}"
$SAFE_TOPIC = $TOPIC -replace '[ /]', '__'
$SAFE_CATEGORY = $CATEGORY -replace '[ /]', '__'
$AGENT_DIR = "$env:OBSIDIAN_VAULT_PATH"
$RAG_MANIFEST = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag/manifest.json"
$SOURCE_DIR = "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources"

if (Test-Path $RAG_MANIFEST) {
    Write-Host "✅ RAG 존재: $SAFE_CATEGORY/$SAFE_TOPIC"
    $MANIFEST_PY = $RAG_MANIFEST -replace '\\', '/'
    python -c "
import json
m = json.load(open('$MANIFEST_PY'))
print(f'  📄 파일 수: {m.get(\"file_count\", 0)}개')
print(f'  📦 크기: {int(m.get(\"total_bytes\",0)/1024)} KB')
print(f'  🕐 최종 업데이트: {m.get(\"updated\",\"\")[:10]}')
"
} else {
    Write-Host "❌ RAG 없음. 세미나 주제에 대한 사전 지식이 없습니다."
}
```

</tab>
</tabs>

### Step 2-2: [조건부] 사전 지식 수집 여부 결정

**RAG가 없는 경우** 사용자에게 질문합니다:

```
❓ 세미나 주제 '{TOPIC}'에 대한 사전 자료가 없습니다.
   웹 검색으로 배경 지식을 미리 수집할까요?
   (y = 수집 후 시작 / n = 수집 없이 바로 시작)
```

**`y` 입력 시**: 아래 검색 실행 후 Step 2-3으로

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python3 "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
  --query "$TOPIC" \
  --output-dir "$SOURCE_DIR" \
  --max-results 5 \
  --search-depth advanced \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" \
  --min-content-length 300

python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
  --topic "$TOPIC" \
  --sources-dir "$SOURCE_DIR" \
  --output-dir "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag" \
  --vault-path "$OBSIDIAN_VAULT_PATH" \
  --category "$CATEGORY"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" `
  --query "$TOPIC" `
  --output-dir "$SOURCE_DIR" `
  --max-results 5 `
  --search-depth advanced `
  --use-jina `
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" `
  --min-content-length 300

python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" `
  --topic "$TOPIC" `
  --sources-dir "$SOURCE_DIR" `
  --output-dir "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH" `
  --category "$CATEGORY"
```

</tab>
</tabs>

**`n` 입력 시**: RAG 없이 Phase 3으로 진행 (보강 없이 분류·저장만 수행)

### Step 2-3: 소스 경로 로드

RAG가 있는 경우 manifest에서 `SOURCE_DIRS`를 추출합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f "$RAG_MANIFEST" ]; then
    SOURCE_DIRS=$(python3 -c "
import json, os
m = json.load(open('$RAG_MANIFEST'))
vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
dirs = [os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])]
print(','.join(dirs))
")
    echo "📁 소스 경로 로드 완료: $SOURCE_DIRS"
    HAS_RAG=true
else
    HAS_RAG=false
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (Test-Path $RAG_MANIFEST) {
    $MANIFEST_PY2 = $RAG_MANIFEST -replace '\\', '/'
    $SOURCE_DIRS = python -c "
import json, os
m = json.load(open('$MANIFEST_PY2'))
vault = m.get('vault_path') or os.environ.get('OBSIDIAN_VAULT_PATH', '')
dirs = [os.path.join(vault, d) if not os.path.isabs(d) else d for d in m.get('source_dirs', [])]
print(','.join(dirs))
"
    Write-Host "📁 소스 경로 로드 완료: $SOURCE_DIRS"
    $HAS_RAG = $true
} else {
    $HAS_RAG = $false
}
```

</tab>
</tabs>

---
created: 2026-03-10
updated: 2026-03-10

## Phase 3: 실시간 Q&A 캡처 루프 ⭐

세션 시작 안내를 출력합니다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎙️ 세미나 캡처 시작
   주제: {TOPIC}
   발표자: {SPEAKER | "미지정"}
   카테고리: {CATEGORY}
   RAG: {HAS_RAG ? "✅ 보강 활성화" : "⚠️ 보강 없음 (저장만)"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

입력 방법:
  [Q] 질문 내용      — 세미나 중 나온 질문
  [O] 의견 내용      — 발표자/청중의 의견·주장
  [A] 답변 내용      — 앞선 질문에 대한 답변
  [!] 중요 사항      — 놓치면 안 될 핵심 내용
  태그 없이 입력하면 AI가 자동 분류합니다.

  '종료', 'exit', '그만' → 세션 종료
```

### Step 3-1: 사용자 입력 대기

> **"📝 입력 (태그 선택 또는 자유 입력):"**

사용자 입력을 `INPUT_RAW`에 저장합니다.

### Step 3-2: 입력 분류

입력 내용을 분석하여 유형을 결정합니다.

| 접두어 | 분류 | 아이콘 |
|---
created: 2026-03-10
updated: 2026-03-10-----|------|--------|
| `[Q]` 또는 `?`로 끝남 | Question (질문) | ❓ |
| `[O]` | Opinion (의견) | 💬 |
| `[A]` | Answer (답변) | ✅ |
| `[!]` | Key Point (핵심) | ⭐ |
| 태그 없음 | AI 자동 분류 | (위 중 하나) |

**자동 분류 기준:**
- 의문문 형태 → ❓ Question
- "~라고 생각", "~인 것 같다", "~이 중요하다" → 💬 Opinion
- 특정 사실 진술, 수치, 메커니즘 설명 → ⭐ Key Point

`ENTRY_TYPE`과 정제된 `INPUT_TEXT`를 결정합니다.

### Step 3-3: [조건부] RAG 맥락 보강

`HAS_RAG=true`인 경우에만 실행합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ "$HAS_RAG" = "true" ]; then
    # 1. 단일 소스 디렉토리 (SOURCE_DIRS가 쉼표로 구분된 문자열일 경우 처리)
    IFS=',' read -ra DIRS <<< "$SOURCE_DIRS"
    for dir in "${DIRS[@]}"; do
        echo "=== 🗂️ Obsidian RAG 검색: [$dir] ==="
        python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
          --query "{INPUT_TEXT}" \
          --sources-dir "$dir" \
          --top-k 3 \
          --chunk-size 800
    done
fi

# 2. Vault 지식 그래프 (Multi-hop 연계 검색)
echo "=== 🕸️ Vault 지식 그래프(Multi-hop) 연계 검색 ==="
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" \
  --query "{INPUT_TEXT}" \
  --top-k 3 \
  --threshold 0.3

# 3. Mem0 동적 기억 하이브리드 검색
echo "=== 🧠 Mem0 동적 기억 하이브리드 검색 ==="
if [ -n "$ANTHROPIC_API_KEY" ]; then
  python3 "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" \
    --query "{INPUT_TEXT}" \
    --limit 3
else
  echo "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 하이브리드 검색 건너뜀"
fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if ($HAS_RAG) {
    # 1. 단일 소스 디렉토리 (SOURCE_DIRS가 쉼표로 구분된 문자열일 경우 처리)
    $DIRS = $SOURCE_DIRS -split ','
    foreach ($dir in $DIRS) {
        Write-Host "=== 🗂️ Obsidian RAG 검색: [$dir] ==="
        python "$env:AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" `
          --query "{INPUT_TEXT}" `
          --sources-dir "$dir" `
          --top-k 3 `
          --chunk-size 800
    }
}

# 2. Vault 지식 그래프 (Multi-hop 연계 검색)
Write-Host "=== 🕸️ Vault 지식 그래프(Multi-hop) 연계 검색 ==="
python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_search.py" `
  --query "{INPUT_TEXT}" `
  --top-k 3 `
  --threshold 0.3

# 3. Mem0 동적 기억 하이브리드 검색
Write-Host "=== 🧠 Mem0 동적 기억 하이브리드 검색 ==="
if ($env:ANTHROPIC_API_KEY) {
    python "$env:AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" `
      --query "{INPUT_TEXT}" `
      --limit 3
} else {
    Write-Host "ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 하이브리드 검색 건너뜀"
}
```

</tab>
</tabs>

### Step 3-4: 심층 해석 및 보강된 항목 생성 (Detailed Synthesis)

사용자의 짧은 입력이나 단편적인 메모를 있는 그대로 기록하지 마십시오. RAG 검색 결과(또는 이전 컨텍스트)를 바탕으로 사용자의 의도를 전문가의 시각에서 **심층적으로 해석(Interpret)**하고, 이를 **논문 수준의 상세한 지식(Detailed Synthesis)**으로 확장하여 작성해야 합니다.

**보강 작성 핵심 규칙:**
- **심층 해석**: 사용자의 입력을 트리거로 삼아, 해당 개념이 전체 아키텍처나 이론에서 갖는 의미, 발생할 수 있는 병목, 해결책 등을 상세히 풀어씁니다.
- **RAG 적극 활용**: 검색된 청크의 구체적인 원리, 수치, 아키텍처적 특징을 반드시 포함하여 내용을 풍성하게 만듭니다.
- **구조화된 리포트 형식**: 단순히 1~2문장 추가가 아니라, [개념 설명] - [구조적 특징] - [시사점/한계] 등의 형태로 짜임새 있게 작성합니다.
- Question: 질문의 표면적 의미를 넘어, 해당 질문이 제기된 학술적/기술적 배경과 그에 대한 심층적 분석을 제공.
- Opinion/Key Point: 단편적 주장을 RAG 기반의 기술적 근거, 장단점 분석, 실제 논문 사례 등과 결합하여 완결된 형태의 지식 단위로 재작성.
- Answer: 답변의 원리를 RAG 데이터를 통해 단계별로 상세히 증명 및 해설.

**출력 형식 (각 항목):**

```
{ENTRY_TYPE_ICON} [{ENTRY_TYPE}] {INPUT_TEXT}

**[전문가 심층 분석 & RAG 보강]**
{여기에 사용자의 입력을 해석하여 확장한, 전문적이고 상세한 분석 리포트 내용을 작성합니다. 여러 문단과 글머리 기호를 활용해 풍부하게 구성하세요.}

📄 출처: {파일명} (score={s:.3f})  ← RAG 있을 때만
```

**세션 내 전체 항목을 `SESSION_LOG`에 누적합니다.**

### Step 3-5: Obsidian 즉시 저장 (append)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

python3 "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{TOPIC}_seminar" \
  --content "{보강된_항목_내용}" \
  --summary "{ENTRY_TYPE}: {INPUT_TEXT 앞 50자}" \
  --category "$CATEGORY" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" \
  --realtime
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}_seminar" `
  --content "{보강된_항목_내용}" `
  --summary "{ENTRY_TYPE}: {INPUT_TEXT 앞 50자}" `
  --category "$CATEGORY" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" `
  --realtime
```

</tab>
</tabs>

저장 확인 후 다음을 출력합니다:

```
💾 저장 완료 ({SESSION_LOG의 총 항목 수}번째 항목)
[계속] 다음 입력을 기다립니다...
```

### Step 3-6: 루프 반복

Step 3-1로 돌아가 입력을 계속 받습니다.

종료 키워드(`종료`, `exit`, `quit`, `그만`, `끝`, `done`) 감지 시 Phase 4로 이동합니다.

---
created: 2026-03-10
updated: 2026-03-10

## Phase 4: 세션 요약 및 마무리

### Step 4-1: 세션 통계 집계

`SESSION_LOG`를 분석하여 항목 유형별 개수를 집계합니다.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 세미나 캡처 완료
   주제: {TOPIC}
   총 {N}개 항목 캡처
   ❓ 질문: {Q_COUNT}개
   💬 의견: {O_COUNT}개
   ✅ 답변: {A_COUNT}개
   ⭐ 핵심: {KEY_COUNT}개
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 4-2: 미답 질문 분석

`SESSION_LOG`에서 `[Q]`(Question) 항목 중 대응하는 `[A]`(Answer)가 없는 항목을 추출합니다.

```
❓ 미답 질문 목록 ({UNANSWERED_COUNT}개):
  1. {질문1}
  2. {질문2}
  ...
```

**미답 질문이 있을 경우** 제안합니다:

```
💡 위 질문들을 후속 연구 주제로 추가하시겠습니까?
   /knowledge_tutor 로 각 질문에 대한 웹 검색을 실행할 수 있습니다.
   (y = 목록 저장 후 계속 / n = 건너뜀)
```

`y` 입력 시: 미답 질문 목록을 별도 섹션으로 노트에 저장합니다.

### Step 4-3: 세션 전체 요약 저장

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

TODAY=$(date +%Y-%m-%d)

# 전체 세션 요약을 누적 노트에 append
python3 "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "{TOPIC}_seminar" \
  --content "{전체_SESSION_LOG_및_미답_질문_목록}" \
  --summary "세미나 완료: {N}항목 ({Q_COUNT}Q / {O_COUNT}O / {KEY_COUNT}Key), 미답 {UNANSWERED_COUNT}개" \
  --category "$CATEGORY" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" \
  --realtime
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }

$TODAY = Get-Date -Format "yyyy-MM-dd"

python "$env:AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" `
  --topic "{TOPIC}_seminar" `
  --content "{전체_SESSION_LOG_및_미답_질문_목록}" `
  --summary "세미나 완료: {N}항목 ({Q_COUNT}Q / {O_COUNT}O / {KEY_COUNT}Key), 미답 {UNANSWERED_COUNT}개" `
  --category "$CATEGORY" `
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC" `
  --realtime
```

</tab>
</tabs>

### Step 4-4: 완료 메시지

```
✅ 세미나 기록 완료!

📁 저장 위치:
  - 세미나 노트: {CATEGORY}/{TOPIC}_seminar.md
  - (RAG 있었다면) 소스: {CATEGORY}/{SAFE_TOPIC}/sources/

❓ 미답 질문 {UNANSWERED_COUNT}개를 추후 연구하려면:
   /knowledge_tutor 실행 후 질문을 주제로 입력하세요.

Obsidian에서 확인해보세요! 🎉
```

---
created: 2026-03-10
updated: 2026-03-10

## 예시 세션

```
USER: /myseminar

AI: 📂 현재 카테고리: PIM, AI, 자율주행

    세미나 주제(Topic)는 무엇인가요?

USER: PIM architecture overview

AI: 발표자(엔터로 건너뜀)?

USER: Dr. Kim

AI: 카테고리 (기본값 Seminar)?

USER: PIM

AI: ✅ RAG 존재: PIM/PIM_architecture_overview (12개 파일, 340KB)

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🎙️ 세미나 캡처 시작
       주제: PIM architecture overview
       발표자: Dr. Kim
       카테고리: PIM
       RAG: ✅ 보강 활성화
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    📝 입력:

USER: DRAM bandwidth bottleneck이 왜 문제가 되는지?

AI: ❓ [Question] DRAM bandwidth bottleneck이 왜 문제가 되는지?

    [RAG 보강] 메모리 대역폭 병목(memory wall)은 현대 AI/HPC 워크로드에서
    핵심 제약 요소입니다. 수집된 자료에 따르면, 최신 GPU는 수십 TB/s의
    연산 처리 능력을 갖추고 있지만 DRAM 대역폭은 수 TB/s 수준에 머물러
    연산 유닛이 데이터를 기다리는 시간(memory-bound)이 전체 성능을 결정합니다.
    PIM은 이 격차를 해소하기 위해 연산을 메모리 내부로 이동시킵니다.

    📄 출처: PIM_arch_overview_3.md (score=4.821)

    💾 저장 완료 (1번째 항목)
    [계속] 다음 입력을 기다립니다...

USER: [O] 결국 PIM이 답이지만 프로그래밍 모델이 너무 어렵다

AI: 💬 [Opinion] PIM이 답이지만 프로그래밍 모델이 너무 어렵다

    [RAG 보강] 타당한 지적입니다. 기존 CPU/GPU 프로그래밍 추상화(CUDA, OpenCL)는
    호스트↔장치 메모리 계층을 전제로 설계되어 PIM 환경에 그대로 적용하기 어렵습니다.
    일부 연구(PIM-enabled instructions, UPMEM SDK)가 이 문제를 완화하려 시도하고 있으나
    아직 범용적인 해결책은 없는 상태입니다.

    📄 출처: PIM_programming_challenges_1.md (score=3.214)

    💾 저장 완료 (2번째 항목)

USER: 종료

AI: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    📊 세미나 캡처 완료
       총 2개 항목 캡처
       ❓ 질문: 1개
       💬 의견: 1개
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ❓ 미답 질문 목록 (1개):
      1. DRAM bandwidth bottleneck이 왜 문제가 되는지?

    💡 위 질문들을 후속 연구 주제로 추가하시겠습니까?

USER: y

AI: ✅ 세미나 기록 완료!
    ...
```

---
created: 2026-03-10
updated: 2026-03-10

## Notes

- **RAG 선택적 보강**: 사전 지식이 없어도 워크플로우 실행 가능 (분류·저장만 수행)
- **즉시 저장**: 입력마다 Obsidian에 append → 세미나 중 앱이 꺼져도 데이터 보존
- **미답 질문 추적**: `[Q]`에 대응하는 `[A]`가 없으면 자동으로 미답 목록에 포함
- **후속 연구 연계**: 미답 질문을 `/knowledge_tutor`의 주제로 그대로 활용 가능
- **의존성**: `rank-bm25` (RAG 활성화 시), `tavily-python` (사전 검색 시)
