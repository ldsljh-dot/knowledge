---
description: [Robust] 세미나/메모를 입력받아 표준 RAG(Agent/{Category})를 구축하고 내용을 누적 저장하는 무한 루프 워크플로우
trigger: /seminar
---

# 🎙️ Seminar & Knowledge Capture Workflow (Robust)

이 워크플로우는 사용자의 메모를 입력받아 **표준 지식 베이스 구조**(`Agent/{Category}/{Topic}`)에 안전하게 저장합니다. 지식이 없으면 자동으로 수집하고, 있으면 즉시 활용합니다.

---

## Phase 1: 환경 설정 및 초기화

### Step 1-1: 필수 환경 점검
실행에 필요한 환경 변수와 패키지를 확인합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 1. 환경 변수 로드
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

# 2. 필수 패키지 점검
python3 -c "import tavily, rank_bm25" 2>/dev/null || { echo "📦 Installing dependencies..."; pip install -r "$AGENT_ROOT/requirements.txt"; }
```

</tab>
</tabs>

### Step 1-1: 기존 카테고리 확인

사용자가 정확한 카테고리를 선택할 수 있도록 현재 생성된 지식 베이스 목록을 보여줍니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
echo "📂 현재 사용 가능한 카테고리:"
ls -F "$AGENT_DIR" | grep / | tr -d /
```

</tab>
</tabs>

### Step 1-2: 주제 및 카테고리 확정 (대화형)

사용자에게 명시적으로 질문하여 변수를 확정합니다.

1.  **"오늘 기록할 세미나나 메모의 주제(Topic)는 무엇인가요?"**
2.  **"위 목록 중 어디에 저장할까요? (Category 입력)"**
    *   (목록에 없으면 새로 생성됩니다.)

> **[중요]** 사용자가 카테고리를 입력하지 않으면 기본값 `General`을 사용합니다.

---

## Phase 2: 지식 베이스(RAG) 무결성 검사

### Step 2-1: 경로 계산 및 RAG 확인

입력받은 `TOPIC`과 `CATEGORY`를 기반으로 안전한 파일 경로(`SafeTopic`)를 계산하고 RAG 존재 여부를 확인합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 변수 설정 (사용자 입력값 적용)
TOPIC="{TOPIC}"
CATEGORY="{CATEGORY}"

# Safe Name 변환 (공백 -> _, 특수문자 중 / 등 경로 구분자만 제거)
# 언더스코어(_)는 유지해야 하므로 [:punct:] 전체 삭제 대신 필요한 처리만 수행
SAFE_TOPIC=$(echo "$TOPIC" | tr ' /' '__')
SAFE_CATEGORY=$(echo "$CATEGORY" | tr ' /' '__')

AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"
RAG_MANIFEST="$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag/manifest.json"

if [ -f "$RAG_MANIFEST" ]; then
    echo "✅ RAG_EXISTS=true"
    echo "📂 기존 지식 베이스를 사용합니다: $SAFE_CATEGORY/$SAFE_TOPIC"
else
    echo "❌ RAG_EXISTS=false"
    echo "🌐 새로운 지식 베이스를 생성해야 합니다."
fi
```

</tab>
</tabs>

### Step 2-2: [조건부] 지식 자동 수집 (Tutor Flow)

`RAG_EXISTS=false`인 경우에만 실행하여 중복 수집을 방지합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# RAG가 없을 때만 실행
if [ ! -f "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag/manifest.json" ]; then
    echo "🚀 검색 및 RAG 생성 시작..."
    
    # 1. 웹 검색
    python3 "$AGENT_ROOT/.gemini/skills/tavily-search/scripts/search_tavily.py" \
      --query "$TOPIC technical details overview" \
      --output-dir "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources" \
      --max-results 5 --use-jina
      
    # 2. Manifest 생성
    python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/create_manifest.py" \
      --topic "$TOPIC" \
      --sources-dir "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources" \
      --output-dir "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/rag" \
      --vault-path "$OBSIDIAN_VAULT_PATH" \
      --category "$CATEGORY"
else
    echo "⏩ 이미 RAG가 존재하므로 수집을 건너뜁니다."
fi
```

</tab>
</tabs>

---

## Phase 3: 실시간 메모 루프 (Interaction Loop) ⭐

사용자가 **'종료', 'exit', 'quit', '그만'**을 입력할 때까지 반복합니다.

### Step 3-1: 사용자 메모 입력

> **"📝 기록할 내용을 입력해 주세요. (종료하려면 '종료' 입력)"**

### Step 3-2: RAG 검색 및 지식 합성

입력된 메모(`INPUT_TEXT`)와 RAG 지식을 결합합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
# 입력 텍스트가 '종료' 관련이면 스크립트에서 처리하지 않음 (Agent 레벨에서 루프 탈출)

# RAG 검색 (입력 내용이 질문이 아니더라도 관련 맥락을 찾음)
python3 "$AGENT_ROOT/.gemini/skills/rag-retriever/scripts/retrieve_chunks.py" \
  --query "{INPUT_TEXT}" \
  --sources-dir "$AGENT_DIR/$SAFE_CATEGORY/$SAFE_TOPIC/sources" \
  --top-k 3 \
  --chunk-size 600
```

</tab>
</tabs>

**[Agent Action]**:
검색 결과를 바탕으로 사용자의 메모를 **"전문적인 기술 노트"** 형태로 재구성합니다.
- 단순 기록: "메모리 구조가 중요함"
- 합성 결과: "AI 에이전트에서 **메모리 구조**는 핵심 병목 구간이며, 최신 논문에서는 이를 형태/기능/동역학으로 분류함."

### Step 3-3: Obsidian 누적 저장 (Append)

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/save_to_obsidian.py" \
  --topic "$TOPIC" \
  --content "{합성된_내용}" \
  --summary "{한줄_요약}" \
  --category "$CATEGORY" \
  --vault-path "$AGENT_DIR/$SAFE_CATEGORY" \
  --append
```

</tab>
</tabs>

---

## Phase 4: 안전 종료 및 대시보드 갱신

세션 종료 시 전체 현황을 동기화합니다.

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
echo "📊 대시보드를 업데이트합니다..."
python3 "$AGENT_ROOT/.gemini/skills/obsidian-integration/scripts/generate_dashboard.py" \
  --agent-dir "$AGENT_DIR" \
  --output "$AGENT_DIR/_Dashboard.md"

echo "✅ 모든 세션 기록이 안전하게 저장되었습니다."
echo "📁 파일 위치: $AGENT_DIR/$SAFE_CATEGORY"
```

</tab>
</tabs>

---

## Notes
- **Robustness**: 파일 경로의 특수문자를 자동으로 처리(`SAFE_TOPIC`)하여 OS 오류를 방지합니다.
- **Efficiency**: RAG 존재 여부를 먼저 확인하여 API 비용과 대기 시간을 최소화합니다.
- **Standardization**: 모든 데이터는 프로젝트 표준(`Agent/Category/Topic`)을 따릅니다.
