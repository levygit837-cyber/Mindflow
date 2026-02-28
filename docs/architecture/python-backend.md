# OmniMind Python Backend Architecture

## Overview
OmniMind backend is Python-first and currently `agent-only`.

Core runtime layers:

1. Public API: FastAPI (`python/omnimind_backend/api`) exposing `/v1/*` routes.
2. Internal service boundary: gRPC contract (`python/omnimind_backend/grpc/proto/omnimind_backend.proto`) with local fallback client.
3. Agent runtime: provider abstraction + stream normalization (`python/omnimind_backend/agents`).
4. Persistence: PostgreSQL via SQLAlchemy + Alembic (`python/omnimind_backend/storage`).
5. Async execution: RQ + Redis (`python/omnimind_backend/workers`) for background workloads.

## Product Direction

Per ADR 0002 (`docs/adr/0002-terminal-first-rich-cli.md`), OmniMind adopts:

- terminal-first interaction (`Typer + Rich`) as the main UX channel;
- gradual deprecation of Python desktop frontend (`omnimind_desktop`);
- no `mind` domain in the main runtime.

## Engineering Governance

- Architecture and coding conventions: `docs/architecture/python-engineering-standards.md`
- Architecture Decision Records: `docs/adr/`

## API Contracts (Current)

### Public HTTP

- `POST /v1/agent/chat/stream` (SSE)
- `GET /health`

### Stream Event Contract

`StreamEvent` is emitted with:

- `id`, `seq`, `type`, `mode`, `data`, `meta`

`type` supports:

- `thought`
- `tool_call`
- `tool_result`
- `response`
- `agent_step`
- `done`
- `error`

`meta` carries provider/model/run identifiers and ordering hints (`turnRunId`, `insertBefore`, `firstResponseMarker`).

## Data Model (Current)

Source of truth:

- `python/omnimind_backend/storage/models.py`
- `python/omnimind_backend/storage/migrations/versions/`

Active ORM entities:

- `settings`
- `neural_documents`

## gRPC

- Proto contracts are versioned in `python/omnimind_backend/grpc/proto/omnimind_backend.proto`.
- Generate stubs with `python/scripts/gen_proto.sh`.
- Runtime server scaffold is `python/omnimind_backend/grpc/server.py`.

## Deprecation Boundary

- TypeScript backend is legacy; Python backend is the official runtime.
- `mind` module and related routes are removed from active runtime.
- `omnimind_desktop` is in deprecation path per ADR 0002.
