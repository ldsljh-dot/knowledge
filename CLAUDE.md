# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

KnowledgeEngine is a Claude Code-orchestrated AI learning agent. Claude Code itself acts as the orchestrator — it reads workflow `.md` files in `.gemini/workflows/` and executes the steps, calling Python skill scripts as subprocesses. There is no separate Python orchestrator.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set TAVILY_API_KEY and OBSIDIAN_VAULT_PATH
```

Required environment variables (`.env`):
- `TAVILY_API_KEY` — from app.tavily.com
- `OBSIDIAN_VAULT_PATH` — absolute path to local Obsidian vault

Optional:
- `SEARCH_MAX_RESULTS` (default: 5)
- `SEARCH_DEPTH` (`basic` | `advanced`, default: `advanced`)
- `ANTHROPIC_API_KEY` — required for Mem0 memory skill (Claude Haiku as extraction LLM)
- `MEM0_USER_ID` — shared user ID for cross-agent memory (default: `knowledge_engine`)

## Workflows (triggered as slash commands)

| Command | Workflow file | Purpose |
|---------|--------------|---------|
| `/knowledge_tutor` | `.gemini/workflows/knowledge_tutor.md` | Web search → Socratic tutoring → Obsidian save + Mem0 |
| `/knowledge_query` | `.gemini/workflows/knowledge_query.md` | RAG Q&A over previously collected sources + Mem0 context |
| `/knowledge_dashboard` | `.gemini/workflows/knowledge_dashboard.md` | Show collected topics overview |
| `/knowledge_personal` | `.gemini/workflows/knowledge_personal.md` | Manage personal events/memos via SQLite (accurate, no LLM interpretation) |
| `/knowledge_rm` | `.gemini/workflows/knowledge_rm.md` | Delete collected topics |

**Note:** `.claude/commands/` files are symlinks to `.gemini/workflows/` — edit only `.gemini/workflows/` files. Workflow files contain both bash (Linux/macOS) and PowerShell (Windows) tab sections.

## Skills (Python scripts)

All skills are called from the project root. Scripts auto-load `.env` via `python-dotenv`.

### tavily-search
```bash
python .gemini/skills/tavily-search/scripts/search_tavily.py \
  --query "topic" \
  --output-dir "$OBSIDIAN_VAULT_PATH/Agent/{category}/sources/topic_name" \
  --use-jina \
  --exclude-domains "reddit.com,youtube.com,amazon.com" \
  --max-results 5
```
Outputs: `{output-dir}/{query}_summary_{date}.md` + one `.md` per source.

### rag-retriever
```bash
# Create manifest (after tavily-search)
python .gemini/skills/rag-retriever/scripts/create_manifest.py \
  --topic "topic" \
  --sources-dir "$OBSIDIAN_VAULT_PATH/Agent/{category}/sources/topic_name" \
  --rag-root "$OBSIDIAN_VAULT_PATH/Agent/{category}/rag"

# BM25 chunk retrieval
python .gemini/skills/rag-retriever/scripts/retrieve_chunks.py \
  --query "user question" \
  --sources-dir "$OBSIDIAN_VAULT_PATH/Agent/{category}/sources/topic_name" \
  --top-k 5 \
  --chunk-size 1200 \
  --show-stats
```
Manifests stored at: `{OBSIDIAN_VAULT_PATH}/Agent/{category}/rag/{safe_topic}/manifest.json`

### obsidian-integration
```bash
python .gemini/skills/obsidian-integration/scripts/save_to_obsidian.py \
  --topic "topic" \
  --content "## 💬 학습 기록\n..." \
  --summary "- key point 1\n- key point 2" \
  --category "AI_Study" \
  --vault-path "$OBSIDIAN_VAULT_PATH/Agent"
```
Outputs:
- 세션 노트: `{vault-path}/{category}/{YYYY-MM-DD}_{topic}.md`
- 종합 누적 노트(`--append`): `{vault-path}/{topic}.md`

### personal-db
```bash
# 일정 추가
python .gemini/skills/personal-db/scripts/manage_events.py add \
  --title "팀 미팅" --start "2026-03-28T14:00" --end "2026-03-28T15:00" \
  --tags '["work"]' --source "user"

# 일정 조회
python .gemini/skills/personal-db/scripts/manage_events.py query \
  --date "2026-03-28"

# 메모 추가
python .gemini/skills/personal-db/scripts/manage_memos.py add \
  --title "회의록" --content "내용..." --tags '["work"]'

# 메모 검색
python .gemini/skills/personal-db/scripts/manage_memos.py search \
  --keyword "회의록"
```
DB stored at: `$OBSIDIAN_VAULT_PATH/Agent/personal.db` (shared across all agents)
Uses SQLite WAL mode for concurrent access safety. LLMs never read raw DB — always use these scripts.

### mem0-memory
```bash
# 기억 저장 (세션 종료 시)
python .gemini/skills/mem0-memory/scripts/memory_save.py \
  --content "AI_Study/PyTorch 학습 완료. 핵심: autograd. 미해결: custom hook" \
  --agent "claude" \
  --metadata '{"workflow": "knowledge_tutor", "topic": "PyTorch"}'

# 기억 검색 (세션 시작 시)
python .gemini/skills/mem0-memory/scripts/memory_search.py \
  --query "PyTorch 이전 학습 이력" --limit 3

# 기억 목록
python .gemini/skills/mem0-memory/scripts/memory_list.py --limit 20
```
Requires: `ANTHROPIC_API_KEY`. Vector store: local Qdrant (`~/.mem0/qdrant/`).
All agents share memories via `MEM0_USER_ID=knowledge_engine`.

## Architecture

```
knowledge_tutor workflow:
  Step 0: Load prior context from Mem0 (if ANTHROPIC_API_KEY set)
  Phase 1: Tavily search → RAG manifest creation
  Phase 2: BM25 RAG retrieval per user question → Socratic tutoring loop
  Phase 3: Save session to Obsidian + save summary to Mem0

knowledge_query workflow:
  Step 0: Load related memories from Mem0 (if ANTHROPIC_API_KEY set)
  Phase 1: Load existing RAG manifest (or fall back to collection)
  Phase 2: BM25 Q&A loop using collected sources
  Phase 3: Save session to Obsidian + save Q&A summary to Mem0

knowledge_personal workflow:
  Phase 1: User selects action (events/memos CRUD)
  Phase 2: Execute manage_events.py or manage_memos.py (deterministic SQLite query)
  Phase 3: Display results
```

Three-layer data architecture (all shared across agents):
- **Obsidian** (`$OBSIDIAN_VAULT_PATH/Agent/`) — knowledge output (MD notes, sources, RAG)
- **Mem0** (`~/.mem0/qdrant/`) — AI session context (learning history, unresolved questions)
- **personal.db** (`$OBSIDIAN_VAULT_PATH/Agent/personal.db`) — structured personal data (events, memos)

RAG token reduction strategy: instead of reading full source files (~80k tokens), BM25 retrieves only the top-k relevant chunks (~3-5k tokens, ~94% reduction).

Search quality control: if `relevance_score` is mostly < 0.05 or content is off-topic, delete the output dir and re-run with a more specific English technical query using `--include-domains`.
