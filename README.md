# 🧠 OmniMind

Multi-agent AI engineering assistant with specialized personalities.

## Overview

OmniMind is a multi-agent AI system built for software engineering assistance. It features 7 specialized agent personalities (Coder, Analyst, Researcher, ArchTech, Critic, Creative, SecurityGuard), each with unique system prompts, tool access, and reasoning depth.

## Architecture

| Component | Stack | Location |
|---|---|---|
| **Backend** | Python 3.11+ / FastAPI / gRPC / Redis+RQ / PostgreSQL | `python/omnimind_backend/` |
| **Frontend** | React 19 / Vite / TypeScript / Framer Motion | `frontend/` |
| **CLI** | Typer | `python/omnimind_cli/` |
| **Desktop** | PySide6 / QML | `python/omnimind_desktop/` |

## LLM Providers

- **Google/VertexAI** (Gemini) — default
- **Anthropic** (Claude)
- **OpenAI** (GPT)
- **Ollama** (local models)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis (optional, for background workers)

### Backend Setup

```bash
cd python
pip install -e ".[dev]"
cp ../.env.example ../.env  # Configure your API keys
python -m omnimind_backend.main
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

- `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` — for Gemini/VertexAI
- `ANTHROPIC_API_KEY` — for Claude
- `OPENAI_API_KEY` — for GPT
- `DATABASE_URL` — PostgreSQL connection string

## Agent Personalities

| Agent | Focus | Tools | Sandbox |
|---|---|---|---|
| **Coder** | Implementation | Filesystem, Shell | Full |
| **Analyst** | Data & Metrics | Code Analysis, Filesystem | None |
| **Researcher** | Information Synthesis | Web Search | None |
| **ArchTech** | System Design | Filesystem, Code Analysis | None |
| **Critic** | Code Review | Code Analysis | None |
| **Creative** | Divergent Thinking | Code Analysis, Filesystem | None |
| **SecurityGuard** | Security Analysis | Code Analysis, Filesystem | Read-Only |

## Key Features

- **Decomposition Thinking** — Complex tasks are broken into a DAG of sub-tasks, scheduled via topological sort, and resolved by specialized agents
- **Multi-Provider Fallback** — Automatic fallback between VertexAI API-key and Service Account auth
- **Memory System** — Per-agent rolling memory with summary windows and RAG retrieval
- **Feature Flags** — 10+ flags for incremental development

## License

Proprietary — Levy Group
