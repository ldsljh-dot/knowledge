# 🎓 KnowledgeEngine

**Claude Code / Cursor 기반 AI 학습 에이전트**  
Tavily 웹 검색 → Socratic 튜터링 → Obsidian 저장을 `/knowledge_tutor` 한 명령으로 실행합니다.

---

## 구조

```
KnowledgeEngine/
├── .agent/
│   ├── workflows/
│   │   └── knowledge_tutor.md    ← Claude Code가 읽는 워크플로우 정의
│   └── skills/
│       ├── tavily-search/        ← 웹 검색 스킬
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── search_tavily.py
│       └── obsidian-integration/ ← Obsidian 저장 스킬
│           ├── SKILL.md
│           └── scripts/
│               └── save_to_obsidian.py
├── .env.example
├── requirements.txt
└── README.md
```

**Claude Code가 오케스트레이터입니다.**  
별도의 Python 오케스트레이터 없이 `knowledge_tutor.md` 워크플로우를 읽고 단계별로 실행합니다.

---

## 셋업

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에서 TAVILY_API_KEY와 OBSIDIAN_VAULT_PATH 입력

# 3. (선택) 환경변수 확인
source .env
echo "Tavily: ${TAVILY_API_KEY:0:10}..."
echo "Vault : $OBSIDIAN_VAULT_PATH"
```

---

## 실행

Claude Code 또는 Cursor에서 이 프로젝트를 열고:

```
/knowledge_tutor
```

또는 채팅창에서:

```
knowledge_tutor 워크플로우를 실행해줘
```

### 실행 흐름 예시

```
AI: 어떤 주제를 학습하시겠습니까?

나: PyTorch FX Graph 구조와 MLIR 변환

AI: 🔍 검색 중...
    ✅ 6개 자료 수집 완료:
      1. pytorch_FX_Graph_구조와_MLIR_변환_summary_2026-02-19.md
      2. pytorch_FX_Graph_구조와_MLIR_변환_1_2026-02-19.md
      ...

    수집한 정보를 기반으로 학습을 시작하시겠습니까?

나: 네

AI: PyTorch FX(Functional Transformation)는 Python 코드를 symbolic하게
    trace하여 `torch.fx.Graph` 객체로 표현합니다.

    Graph는 여러 Node로 구성되며, 각 Node의 op 종류는:
    - placeholder: 함수 입력
    - call_function: torch.add 같은 함수 호출
    - call_method: tensor.relu() 같은 메서드 호출
    - call_module: nn.Linear 같은 모듈 호출
    - output: 출력

    💡 확인 질문: MLIR 변환 시 call_module과 call_function은
    어떻게 다르게 처리해야 할까요?

나: call_module은 nn.Module의 weight/bias 파라미터 정보가 있어서
    MLIR의 func.func로 별도 정의해야 할 것 같습니다

AI: 정확합니다! call_module은 파라미터를 포함하므로 MLIR에서
    `func.func @forward(%arg0: tensor<...>)`로 변환하고
    weight는 `ml_program.global`로 선언하는 패턴이 일반적입니다.

    💡 그렇다면 FX Graph의 Node를 순서대로 순회할 때
    `graph.nodes`를 쓰면 위상 정렬(topological order)이 보장될까요?

나: 종료

AI: 💾 Obsidian 저장 중...
    ✅ 완료!
    📁 /vault/2026-02-19_PyTorch_FX_Graph_구조와_MLIR_변환.md
```

---

## Skill 개별 실행

```bash
# Tavily 검색만
cd .agent/skills/tavily-search
python scripts/search_tavily.py \
  --query "MLIR affine dialect" \
  --output-dir "$OBSIDIAN_VAULT_PATH/sources/MLIR_affine"

# Obsidian 저장만
cd .agent/skills/obsidian-integration
python scripts/save_to_obsidian.py \
  --topic "MLIR affine dialect" \
  --content "## 💬 학습 기록\n### Q1: ..." \
  --summary "- affine.for는 정적 루프 변환에 사용\n- ..." \
  --category "AI_Study" \
  --vault-path "$OBSIDIAN_VAULT_PATH"
```

---

## 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `TAVILY_API_KEY` | ✅ | [app.tavily.com](https://app.tavily.com) 에서 발급 |
| `OBSIDIAN_VAULT_PATH` | ✅ | 로컬 Obsidian vault 절대경로 |
| `SEARCH_MAX_RESULTS` | ❌ | 검색 결과 수 (기본: 5) |
| `SEARCH_DEPTH` | ❌ | `basic` \| `advanced` (기본: `advanced`) |
