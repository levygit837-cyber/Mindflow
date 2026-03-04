# OmniMind

Multi-agent AI engineering assistant with specialized personalities.

## Overview

OmniMind is a multi-agent AI system built for software engineering assistance. It features specialized agent personalities (Coder, Analyst, Researcher, Orchestrator), each with unique system prompts, tool access, and reasoning depth. Complex tasks are decomposed into a DAG of sub-tasks, scheduled via topological sort, and resolved by the most appropriate agent.

## Architecture

| Component | Stack | Location |
|---|---|---|
| **Backend** | Python 3.11+ / FastAPI / LangGraph / gRPC / Redis+RQ / PostgreSQL 16 | `python/omnimind_backend/` |
| **Frontend** | React 19 / Vite / TypeScript | `frontend/` |
| **CLI** | Typer + Rich | `python/omnimind_cli/` |

### Request Flow

```
Frontend (React/Vite :5173)
    │  HTTP POST /v1/agent/chat/stream (SSE)
    ▼
api/v1/agent.py          — FastAPI router
    ▼
orchestrator/router.py   — AgentType selection → OrchestratorDecision
    ▼
orchestrator/graph.py    — LangGraph DAG execution
    ▼
agents/personalities/    — Specialized agent implementations
    ▼
runtime/providers.py     — LLM provider adapters
    ▼
storage/repositories.py  — SQLAlchemy (PostgreSQL)
```

## LLM Providers

- **Google/VertexAI** (Gemini) — default
- **Anthropic** (Claude)
- **OpenAI** (GPT)
- **Ollama** (local models)

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+
- PostgreSQL 16
- Redis (for background workers)

### Backend Setup

```bash
cd python
uv sync
cp ../.env.example ../.env   # Configure your API keys

uv run omnimind-api          # FastAPI on :8000
uv run omnimind-grpc         # gRPC on :50051
uv run omnimind-worker       # RQ background worker

# Apply DB migrations
uv run alembic upgrade head
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev     # Vite on :5173
```

### Full Dev Stack

```bash
./start_dev.sh  # gRPC → API → Vite (from project root)
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

- `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` — for Gemini/VertexAI
- `ANTHROPIC_API_KEY` — for Claude
- `OPENAI_API_KEY` — for GPT
- `DATABASE_URL` — PostgreSQL connection string (default: `localhost:5433/omnimind_v1`)
- `REDIS_URL` — Redis connection string (default: `localhost:6380`)

### Local Infrastructure (Docker)

```bash
docker-compose up -d   # PostgreSQL, Redis, SearXNG
```

| Service | Default Address |
|---|---|
| PostgreSQL | `localhost:5433` — DB: `omnimind_v1` |
| Redis | `localhost:6380` |
| SearXNG | `localhost:8080` |

## Agent Personalities

| Agent | Focus | Tools | Sandbox |
|---|---|---|---|
| **Coder** | Implementation | Filesystem, Shell | Full |
| **Analyst** | Data & Metrics | Code Analysis, Filesystem | None |
| **Researcher** | Information Synthesis | Web Search | None |
| **Orchestrator** | Task Decomposition & Delegation | — | None |

Sub-personalities (`security_guard`, `critic`) are composed via prompt injection into the Analyst agent.

## Key Features

- **Decomposition Thinking** — Complex tasks broken into a DAG of sub-tasks, scheduled via topological sort, resolved by specialized agents
- **Multi-Provider Fallback** — Automatic fallback between VertexAI API-key and Service Account auth
- **Memory System** — Per-agent rolling memory with summary windows and RAG retrieval (PostgreSQL-backed)
- **Context Governance** — Token budget management (`max_payload_tokens = 10_000`)
- **Session Review** — Automatic session chunk review via Analyst critic sub-personality
- **Feature Flags** — Incremental rollout via `infra/config.py`

## Quality Checks

```bash
cd python
make format     # ruff check --fix + ruff format
make lint       # ruff check
make typecheck  # mypy
make test       # pytest
make check      # all of the above
```

## License

Proprietary
