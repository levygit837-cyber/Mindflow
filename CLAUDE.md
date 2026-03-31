<!-- gitnexus:start -->
# GitNexus MCP

This project is indexed by GitNexus as **MindFlow** (93539 symbols, 234822 relationships, 300 execution flows).

## Always Start Here

1. **Read `gitnexus://repo/{name}/context`** — codebase overview + check index freshness
2. **Match your task to a skill below** and **read that skill file**
3. **Follow the skill's workflow and checklist**

> If step 1 warns the index is stale, run `npx gitnexus analyze` in the terminal first.

## Skills

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

---

# MindFlow Project Guide

## Tech Stack

**Backend (Python 3.11+):** FastAPI + gRPC + LangGraph agents + PostgreSQL (pgvector) + RabbitMQ + KuzuDB graph storage

**Frontend:** React 19 + TypeScript + Vite 8 + Tailwind v4 + Zustand

**Package Managers:** `uv` for Python (NOT pip/poetry), `npm` for frontend

## Essential Commands

**Backend (from `/python/`):**
- `uv sync` - Install dependencies
- `uv run mindflow-api` - Start FastAPI (port 8000)
- `uv run mindflow-grpc` - Start gRPC (port 50051)
- `uv run mindflow-worker` - Start RabbitMQ worker
- `make check` - Run all quality checks (format, lint, typecheck, test)
- `make format` - Auto-fix with ruff
- `uv run alembic upgrade head` - Run database migrations

**Frontend (from `/frontend/`):**
- `npm run dev` - Vite dev server (port 5173)
- `npm run lint` - ESLint check
- `npm run test` - Vitest unit tests
- `npm run test:e2e` - Playwright e2e tests

**Full Stack (from root):**
- `./start_dev.sh` - Start all services (Docker + API + Frontend + Worker)
- `./stop_dev.sh` - Stop all services
- `./status_dev.sh` - Check service status

## Critical Gotchas

1. **Always use `uv run` for Python commands** - This project uses `uv`, not pip or poetry
2. **Non-standard ports** - PostgreSQL on 5433 (not 5432), RabbitMQ on 5673 (not 5672)
3. **Tailwind v4 syntax** - Uses new `@import 'tailwindcss'` in CSS, no separate config file
4. **Multi-service coordination** - Backend has 3 processes (API, gRPC, worker) that must run together
5. **Feature flags** - Many features are toggled via env vars (ENABLE_RABBITMQ, ENABLE_LLM_PLANNING_TRIGGER, etc.)
6. **Agent iteration limits** - Configurable up to 1000 iterations (see UNLIMITED_AGENTS_GUIDE.md)

## Code Style

**Python:**
- Line length: 100 characters
- Indentation: 4 spaces
- Use ruff for formatting and linting
- Type hints required (mypy strict mode disabled but encouraged)

**TypeScript:**
- Indentation: 2 spaces
- ESLint 9 flat config with typescript-eslint
- Strict mode enabled

## Testing

- **Always run tests after making changes** - Use `make check` (Python) or `npm run test` (frontend)
- Python tests in `python/tests/` with markers: `@pytest.mark.live`, `@pytest.mark.slow`, `@pytest.mark.integration`
- Frontend uses Vitest for unit tests, Playwright for e2e
- Coverage threshold: 80% for Python

## Git Workflow

- **Commit style:** Conventional Commits (feat:, fix:, docs:, refactor:, test:, chore:)
- Always include Co-Authored-By line for AI commits
- Test before committing

## Environment Setup

Required env vars (see `.env.example`):
- `DATABASE_URL` - PostgreSQL connection
- `RABBITMQ_URL` - RabbitMQ AMQP connection
- `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` - Vertex AI auth
- `MINDFLOW_ALLOWED_PATHS` - Filesystem allowlist for agents
