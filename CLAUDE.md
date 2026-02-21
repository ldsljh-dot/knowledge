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

## Workflows (triggered as slash commands)

| Command | Workflow file | Purpose |
|---------|--------------|---------|
| `/knowledge_tutor` | `.gemini/workflows/knowledge_tutor.md` | Web search → Socratic tutoring → Obsidian save |
| `/knowledge_query` | `.gemini/workflows/knowledge_query.md` | RAG Q&A over previously collected sources (no new web search) |
| `/knowledge_dashboard` | `.gemini/workflows/knowledge_dashboard.md` | Show collected topics overview |

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

## Architecture

```
knowledge_tutor workflow:
  Phase 1: Tavily search → RAG manifest creation
  Phase 2: BM25 RAG retrieval per user question → Socratic tutoring loop
  Phase 3: Save session to Obsidian

knowledge_query workflow:
  Phase 1: Load existing RAG manifest (or fall back to collection)
  Phase 2: BM25 Q&A loop using collected sources
  Phase 3: Optional Obsidian save
```

RAG token reduction strategy: instead of reading full source files (~80k tokens), BM25 retrieves only the top-k relevant chunks (~3-5k tokens, ~94% reduction).

Search quality control: if `relevance_score` is mostly < 0.05 or content is off-topic, delete the output dir and re-run with a more specific English technical query using `--include-domains`.
