# OmniMind Python Backend Architecture

## Overview
OmniMind backend is now defined as a Python-first architecture with the following core layers:

1. Public API: FastAPI (`python/omnimind_backend/api`) exposing `/v1/*` endpoints.
2. Internal transport: gRPC contracts (`python/omnimind_backend/grpc/proto/omnimind_backend.proto`).
3. Async jobs: RQ + Redis (`python/omnimind_backend/workers`).
4. Persistence: PostgreSQL via SQLAlchemy + Alembic (`python/omnimind_backend/storage`).
5. Agent runtime: LangChain/LangGraph/DeepAgents integration (`python/omnimind_backend/agents`).
6. Swarm runtime: real orchestrator service in Python (`python/omnimind_backend/swarm`).

## Engineering Governance
- Architecture and coding conventions: `docs/architecture/python-engineering-standards.md`
- Architecture Decision Records: `docs/adr/`

## API Contracts
### Agent
- `POST /v1/agent/chat/stream` (SSE)
- `GET /v1/agent/logs/stream` (SSE)
- `GET /v1/agent/conversations`
- `POST /v1/agent/conversations`
- `DELETE /v1/agent/conversations?id=...`
- `GET /v1/agent/conversations/{conversation_id}/messages`

### Settings
- `GET /v1/settings`
- `PUT /v1/settings`

### Swarm
- `POST /v1/swarm/tasks`
- `GET /v1/swarm/tasks/{task_id}`
- `GET /v1/swarm/tasks/{task_id}/stream` (SSE)

## Data Model
The initial schema is in:
- `python/omnimind_backend/storage/models.py`
- `python/omnimind_backend/storage/migrations/versions/20260227_0001_initial.py`

Tables:
- `settings`
- `conversations`
- `messages`
- `swarm_tasks`
- `swarm_events`

## Eventing
- Agent logs are appended to Redis stream key: `omnimind:agent:logs`.
- Swarm task live updates are published on channel: `omnimind:swarm:{task_id}`.
- Swarm events are persisted in Postgres (`swarm_events`) for replay and audit.

## Worker Flow
1. API creates `swarm_tasks` row.
2. API enqueues `omnimind_backend.workers.tasks.run_swarm_task`.
3. RQ worker executes `SwarmRuntimeService.run_task`.
4. Service updates DB snapshots and publishes events to Redis.

## gRPC
- Proto contracts are versioned in `python/omnimind_backend/grpc/proto/omnimind_backend.proto`.
- Generate stubs with `python/scripts/gen_proto.sh`.
- Runtime server scaffold is `python/omnimind_backend/grpc/server.py`.

## Deprecation Boundary
TypeScript backend is legacy. Python backend is the official runtime moving forward.
Legacy swarm under `src/server/swarm/*` has been removed.
