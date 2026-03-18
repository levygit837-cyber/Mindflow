# Technology Stack

**Analysis Date:** 2025-02-21

## Languages

**Primary:**
- Python >=3.11 - Used for backend orchestrator logic, workers, agents, and prompt management (`mindflow_backend`).

**Secondary:**
- TypeScript - Used for frontend interfaces (observed in repository structure, e.g., `frontend/`).

## Runtime

**Environment:**
- Python 3.11+ (AsyncIO heavily utilized)

**Package Manager:**
- uv / pip (lockfile: `uv.lock`)
- Lockfile: present

## Frameworks

**Core:**
- FastAPI 0.116.0 - Backend API layer for exposing task and orchestration endpoints (`mindflow-api`).
- LangGraph 0.2.67 - DAG-based state machine for multi-agent workflow execution and orchestrator task decomposition.
- LangChain 0.3.27 - Agent framework for managing LLM interactions, tools, and dynamic prompts.
- Pydantic 2.11.7 - Data validation and core schemas for Todo Planning (`TodoItemContract`, `TodoListContract`).

**Testing:**
- Pytest 8.4.1 - Test runner for unit and E2E tests (`python/tests/`).
- Pytest-Asyncio 1.1.0 - Async testing support.

**Build/Dev:**
- Ruff 0.12.11 - Fast Python linting and formatting.
- Mypy 1.17.1 - Static type checking for Python codebase.
- Setuptools - Build backend specified in `pyproject.toml`.

## Key Dependencies

**Critical:**
- `langgraph-checkpoint-postgres` 2.0.15 - Persistence layer for saving LangGraph orchestrator session states.
- `aio-pika` 9.4.1 / `pika` 1.3.2 - RabbitMQ clients for orchestrator workers (`OrchestratorWorker`).
- `grpcio` 1.74.0 - Used for fast RPC communication across the system (`mindflow-grpc`).

**Infrastructure:**
- `psycopg` 3.2.9 / `asyncpg` 0.31.0 - PostgreSQL drivers for async database access.
- `kuzu` 0.5.0 - Embedded graph database integration.

## Configuration

**Environment:**
- `pydantic-settings` 2.10.1 - Used for typed, validated environment configurations.
- Environment variables (usually `.env`).

**Build:**
- `python/pyproject.toml` - Central configuration for dependencies, Ruff, Pytest, and Mypy.
- `python/pytest.ini` - Additional test configurations.

## Platform Requirements

**Development:**
- Python >=3.11
- Docker & Docker Compose (for services like PostgreSQL, RabbitMQ).

**Production:**
- Linux container environments (Docker).
- PostgreSQL database.
- RabbitMQ message broker.

---

*Stack analysis: 2025-02-21*
