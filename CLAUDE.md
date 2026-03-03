# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

All Python commands are run from the `python/` directory using `uv`.

### Backend

```bash
# Install dependencies
cd python && uv sync

# Run services individually
uv run omnimind-api          # FastAPI on :8000
uv run omnimind-grpc         # gRPC on :50051
uv run omnimind-worker       # RQ background worker

# Apply DB migrations
uv run alembic upgrade head

# Full dev stack (gRPC → API → Vite frontend)
./start_dev.sh
```

### Quality checks (must pass before commit)

```bash
cd python

make format       # ruff check --fix + ruff format
make lint         # ruff check
make typecheck    # mypy omnimind_backend omnimind_cli omnimind_desktop
make test         # pytest
make check        # all of the above in sequence
```

### Tests

```bash
# All tests
cd python && uv run pytest

# Single file
uv run pytest tests/test_agent_personalities.py -v

# Live integration (requires credentials)
RUN_LIVE_VERTEX_TESTS=1 uv run pytest tests/live/test_vertex_agent_stream_live.py -v -s
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # Vite on :5173
npm run build
npm run lint
```

---

## Architecture

### Technology Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.11+, FastAPI, LangChain + LangGraph, PostgreSQL 16, Redis + RQ |
| LLM providers | VertexAI/Gemini (default), Anthropic, OpenAI, Ollama |
| Frontend | React 19, Vite, TypeScript |
| CLI | Typer + Rich |
| Desktop | PySide6/QML — **legacy, in deprecation; no new features** |
| Transport | HTTP REST + SSE (primary), gRPC (internal) |

### Request Flow

```
Frontend (React/Vite :5173)
    │  HTTP POST /v1/agent/chat/stream (SSE)
    ▼
api/v1/agent.py          — FastAPI router, no business logic
    ▼
orchestrator/router.py   — keyword-based AgentType selection → OrchestratorDecision
    ▼
orchestrator/graph.py    — LangGraph DAG execution
    ▼
agents/personalities/    — 7 agents, each with system prompt + tool scopes
    ▼
runtime/providers.py     — LLM provider adapters (VertexAI, Anthropic, OpenAI, Ollama)
    ▼
storage/repositories.py  — SQLAlchemy (never raw SQL in routes)
```

### Backend Folder Canonical Roles

```
omnimind_backend/
  api/           # FastAPI adapters — no complex business logic
  schemas/       # Pydantic contracts — no framework imports
  agents/        # Personalities, prompts, tool registry — framework-agnostic
    personalities/  # One file per agent: coder, analyst, researcher, arch_tech, critic, creative, security_guard
    prompts/        # System prompts
    tools/          # sandbox.py (filesystem/shell), search_web.py (SearXNG)
  orchestrator/  # Routing, LangGraph DAG, complexity scoring, context governance
  runtime/       # Provider adapters, SSE streaming engine, DeepAgents factory
  memory/        # Per-agent RAG + summarization (PostgreSQL-backed)
  storage/       # SQLAlchemy models, Alembic migrations, repositories
  workers/       # RQ background jobs
  grpc/          # Proto definitions + generated code + service implementations
  infra/         # config.py (Settings), logging, middleware stack, resilience, sanitizer, normalizer
```

### Layer Dependency Rules

- `schemas/*` must NOT import FastAPI, SQLAlchemy, or gRPC.
- `agents/*` must NOT import FastAPI (framework-agnostic).
- `api/*` depends on `schemas`, `agents`, `storage.repositories`, `infra` only.
- `storage/*` is the sole gateway to the database; routes must never write raw SQL.
- `infra/*` is cross-cutting — config, logging, middleware.

### CLI Folder Roles

```
omnimind_cli/
  commands/   # Typer entrypoints — no business logic
  workflows/  # High-level orchestration per command
  render/     # Rich components (panels, tables, progress, timeline)
  clients/    # HTTP/SSE clients with reconnect/timeout handling
```

### Agent Personalities

Each personality lives in `agents/personalities/<name>.py` and calls `BaseAgent(...)`.

| Agent | Tools | Sandbox | ThinkingLevel |
|-------|-------|---------|---------------|
| Coder | FILESYSTEM, SHELL | FULL | HIGH |
| Analyst | CODE_ANALYSIS, FILESYSTEM | NONE | MEDIUM |
| Researcher | WEB_SEARCH | NONE | MEDIUM |
| ArchTech | FILESYSTEM, CODE_ANALYSIS | NONE | HIGH |
| Critic | CODE_ANALYSIS | NONE | MEDIUM |
| Creative | CODE_ANALYSIS, FILESYSTEM | NONE | HIGH |
| SecurityGuard | CODE_ANALYSIS, FILESYSTEM | READ_ONLY | HIGH |

Default fallback agent is always **Coder**.

### Orchestrator Routing (Phase 2 — keyword-based)

`orchestrator/router.py` scores each `AgentType` by regex keyword hits in the user message and returns an `OrchestratorDecision`. Phase 3 will replace this with LLM-powered intent classification.

### Feature Flags

All flags live in `infra/config.py` (as `Settings` fields) and default to `False`. Phases:

| Flag | Phase |
|------|-------|
| `ENABLE_CREATIVE_AGENT`, `ENABLE_SECURITY_GUARD_AGENT` | 1 |
| `ENABLE_INPUT_NORMALIZATION`, `ENABLE_CONTEXT_GOVERNANCE`, `ENABLE_SESSION_CHUNKS` | 2 |
| `ENABLE_ASYNC_WORKFLOWS`, `ENABLE_WORKFLOW_REGISTRY` | 3 |
| `ENABLE_DECOMPOSITION_THINKING`, `ENABLE_DT_V2` | 4 |

### Context Governance

- `max_payload_tokens = 10_000` (standardized in ADR 0005)
- `hard_limit_tokens = 1_000_000`
- Memory summarization window: `300_000` tokens
- Memory embedding dims: `256`
- Retrieval top-k: `4`

### Local Infrastructure

```
PostgreSQL: localhost:5433 / DB: omnimind_v1 / user: omnimind_app
Redis:      localhost:6380
SearXNG:    localhost:8080 (docker-compose.yml)
```

---

## Code Conventions

- **Python 3.11+ only.** Use `StrEnum`, `X | Y` union syntax, `from __future__ import annotations`.
- **Absolute imports** everywhere: `from omnimind_backend.infra...`, never relative.
- **Typing is mandatory** on all new public APIs and modules.
- **One primary responsibility per file.**
- **Formatters/linters:** Ruff for format + lint, MyPy for type checking. Pre-commit runs both automatically.
- **Tests** go in `python/tests/test_*.py`. Bug fixes must include regression tests.

## Git Conventions

- **Conventional Commits:** `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- **Branch naming:** `feature/*`, `fix/*`, `refactor/*`, `docs/*`
- **Versioning:** SemVer on the Python package.
- Breaking API/schema changes require an ADR + migration note in the PR.

## ADR Process

- Human-reviewed ADRs → `docs/adr/` (committed, use template `docs/adr/0000-template.md`)
- AI-generated ADRs → `ADR-IA/` (local-only, not committed to git)
- An ADR is required for: layer architecture changes, stack/framework changes, new cross-cutting patterns, deprecation of core modules.

## Definition of Done

A task is complete only when:
1. Architecture pattern followed (layer rules respected)
2. Ruff lint + format pass
3. MyPy type check passes
4. Relevant tests are green
5. Documentation updated if necessary
