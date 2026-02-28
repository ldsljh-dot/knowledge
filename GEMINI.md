# 🎓 KnowledgeEngine: AI Learning Agent

KnowledgeEngine is an AI-driven learning platform designed to automate the process of researching, learning, and documenting complex technical topics. It leverages the orchestration capabilities of agents like Gemini CLI or Claude Code to execute multi-stage workflows involving web search, Socratic tutoring, and knowledge management in Obsidian.

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.8+**
- **Tavily API Key**: Get one at [tavily.com](https://tavily.com).
- **Obsidian**: A local vault set up on your machine.

### 2. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set:
# TAVILY_API_KEY=your_key_here
# OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

### 3. Usage
Run the main workflow using Gemini CLI:
```bash
/knowledge_tutor
```
This triggers the following pipeline:
1. **Search**: Finds high-quality web sources.
2. **RAG**: Indexes the content for efficient retrieval.
3. **Tutor**: Engages in a Socratic dialogue to help you learn.
4. **Save**: Exports the session and sources to your Obsidian vault.

## 🛠 Project Architecture

The project follows a **Workflow + Skill** architecture where the LLM agent acts as the orchestrator.

### Cross-Platform Support
- **OS Detection**: Workflows are designed to detect the current operating system (Linux/macOS vs. Windows) and use the appropriate shell (`bash` or `powershell`).
- **Path Compatibility**: Python scripts use `pathlib` to ensure paths work correctly across all platforms.
- **Environment**: `.env` loading logic is provided for both Bash and PowerShell environments.

### Core Workflows (`.gemini/workflows/`)
- **`knowledge_tutor.md`**: The primary entry point. Orchestrates the full search-learn-save lifecycle.
- **`knowledge_query.md`**: Allows querying previously collected knowledge using RAG without re-searching the web.
- **`myseminar.md`**: Real-time seminar Q&A capture. Classifies inputs (Question/Opinion/Answer/Key Point), enriches with RAG context, and saves to Obsidian. Generates unanswered question list at session end.

### Skills (`.gemini/skills/`)
Skills are standalone Python scripts that perform specific tasks:
- **`tavily-search`**: Uses Tavily for discovery and Jina Reader for deep content extraction (Markdown).
- **`rag-retriever`**: Implements a BM25-based RAG system to provide context for tutoring while minimizing token usage.
- **`obsidian-integration`**: Handles the formatting and saving of notes to the Obsidian vault.

## 📐 Development Conventions

### Python Scripts
- Scripts are designed to be called as subprocesses from the project root.
- They auto-load `.env` and use standard `argparse` for CLI interactions.
- Outputs are typically Markdown files with YAML frontmatter for easy ingestion by Obsidian.

### RAG Strategy
- Instead of feeding entire documents into the LLM, the system uses `retrieve_chunks.py` to fetch relevant segments (~800 characters) based on the user's current question. This reduces context window usage by ~90%+.

### Quality Control
- Workflows include explicit "Garbage Cleanup" steps to verify the relevance of search results before proceeding to the tutoring phase.

## 📝 Key Commands Reference

| Task | Command |
|------|---------|
| **Full Tutor Workflow** | `/knowledge_tutor` |
| **Move Topic** | `/knowledge_mv` |
| **Search Only** | `python .gemini/skills/tavily-search/scripts/search_tavily.py --query "Topic" --output-dir "path"` |
| **Create RAG Index** | `python .gemini/skills/rag-retriever/scripts/create_manifest.py --topic "Topic" --sources-dir "path"` |
| **Retrieve Chunks** | `python .gemini/skills/rag-retriever/scripts/retrieve_chunks.py --query "Question" --sources-dir "path"` |
| **Save to Obsidian** | `python .gemini/skills/obsidian-integration/scripts/save_to_obsidian.py --topic "Topic" ...` |
