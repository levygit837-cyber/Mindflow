# External Integrations

**Analysis Date:** 2025-02-21

## APIs & External Services

**LLM Providers:**
- OpenAI - Primary intelligence for Orchestrator planning, delegation, and reasoning.
  - SDK/Client: `langchain-openai` (0.3.0)
- Anthropic - Alternative LLM provider for specialized tasks.
  - SDK/Client: `langchain-anthropic` (0.3.0)
- Google GenAI / Vertex AI - Additional supported LLM models.
  - SDK/Client: `langchain-google-genai` (2.0.0), `langchain-google-vertexai` (2.0.0)
- Ollama - Supported for local, self-hosted model execution.
  - SDK/Client: `langchain-ollama` (0.3.0)

## Data Storage

**Databases:**
- PostgreSQL
  - Usage: LangGraph check-pointing (`langgraph-checkpoint-postgres`), session state persistence, and vector search.
  - Client: `psycopg`, `asyncpg`, `pgvector`
- KuzuDB
  - Usage: Graph database functionality for mapping complex relationships.
  - Client: `kuzu` (0.5.0)

**Message Broker:**
- RabbitMQ
  - Usage: Asynchronous task queues for workers. The `OrchestratorWorker` processes messages for task decomposition, workflow execution, and agent coordination.
  - Client: `pika`, `aio-pika`

**File Storage:**
- Local filesystem primarily used for workspace context reading by the `analyst` agent.

**Caching:**
- In-memory dictionaries used for short-lived session states (e.g., `TodoPlanningService` in `python/mindflow_backend/services/orchestration/todo_planning_service.py`).

## Authentication & Identity

**Auth Provider:**
- Custom (No specific third-party auth provider like Auth0 or Firebase detected in the core orchestrator scope).

## Monitoring & Observability

**Logs:**
- Approach: Structured JSON logging.
- Client: `structlog` (25.5.0) wrapped by custom internal logger (`mindflow_backend.infra.logging.get_logger`).

## Environment Configuration

**Required env vars:**
- LLM Provider API Keys (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`).
- Database URIs for PostgreSQL.
- Message Broker URIs for RabbitMQ.

**Secrets location:**
- Standard `.env` files (ignored in version control).

---

*Integration audit: 2025-02-21*
