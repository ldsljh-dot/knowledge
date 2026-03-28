---
name: mem0-memory
description: "Mem0 기반 AI 장기 기억 저장·검색. 세션 간 학습 이력, 미해결 질문, 문맥을 유지합니다. Claude/Gemini/ZeroClaw/OpenClaw 모두 같은 저장소 공유. Use when starting/ending a session to load/save context, or when searching for prior learning history."
---

# Mem0 Memory Skill

세션을 껐다 켜도 이전 학습 이력과 문맥을 기억합니다.

**저장소**: 로컬 Qdrant (`~/.mem0/qdrant/`) — 외부 서버 없음
**공유 범위**: `MEM0_USER_ID` 동일 시 모든 에이전트 공유 (기본: `knowledge_engine`)

## 기억 저장 (memory_save.py)

```bash
python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_save.py" \
  --content "AI_Study/PyTorch_autograd 학습 완료. 핵심: computational graph, backward pass. 미해결: custom backward hook 성능 이슈" \
  --agent "claude" \
  --metadata '{"workflow": "knowledge_tutor", "topic": "PyTorch autograd", "category": "AI_Study"}'
```

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `--content` | ✅ | 저장할 기억 내용 (자연어 문장 권장) |
| `--agent` | ✅ | 에이전트 식별자 (`claude`/`gemini`/`zeroclaw`/`openclaw`) |
| `--metadata` | ❌ | 추가 메타데이터 JSON |

## 기억 검색 (memory_search.py)

```bash
# 세션 시작 시 관련 이전 문맥 로드
python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" \
  --query "PyTorch 관련 학습 이력" \
  --limit 3

# 특정 에이전트 기억만 검색
python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_search.py" \
  --query "미해결 질문" --agent "claude" --limit 5
```

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `--query` | ✅ | 검색 쿼리 (자연어) |
| `--agent` | ❌ | 에이전트 필터 |
| `--limit` | ❌ | 최대 결과 수 (기본: 5) |
| `--format` | ❌ | `text` (기본) 또는 `json` |

## 기억 목록 (memory_list.py)

```bash
# 최근 기억 20건 조회
python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_list.py" --limit 20

# Claude 기억만
python "$AGENT_ROOT/.gemini/skills/mem0-memory/scripts/memory_list.py" --agent "claude"
```

## 권장 사용 패턴

| 시점 | 동작 | 스크립트 |
|------|------|----------|
| 세션 시작 | 관련 토픽 이전 문맥 검색 | `memory_search.py` |
| 학습 완료 (tutor) | 학습 요약 + 미해결 질문 저장 | `memory_save.py` |
| Q&A 완료 (query) | 핵심 Q&A 쌍 저장 | `memory_save.py` |
| 대시보드 확인 | 최근 기억 목록 조회 | `memory_list.py` |

## 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | Mem0 내부 LLM 백엔드 (Claude Haiku 사용) |
| `MEM0_USER_ID` | ❌ | 공유 사용자 ID (기본: `knowledge_engine`) |

## 의존성

```
mem0ai>=0.1.0
sentence-transformers>=2.0.0   # 로컬 임베딩 (HuggingFace)
```

설치:
```bash
pip install mem0ai sentence-transformers
```
