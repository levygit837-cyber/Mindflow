# Frontend Roadmap: Migration to Qt (PySide6) + Python

## Objective
After backend migration to Python, the Next.js frontend will be replaced by a desktop-first Qt application using PySide6.

## Why
1. Single-language product stack (Python across backend and frontend logic).
2. Better desktop UX control for developer-oriented workflows.
3. Strong local runtime integration for agent tooling and filesystem-heavy operations.

## Proposed Phases
1. Contract freeze
- Stabilize `/v1/*` backend endpoints and SSE payloads.
- Produce API contract docs for desktop client consumption.

2. Qt shell bootstrap
- Create PySide6 app shell with navigation for Agent, Swarm, Logs, Settings.
- Add HTTP + SSE client layer for FastAPI endpoints.

3. Feature parity
- Agent chat timeline (thought, tool_call, tool_result, response).
- Swarm dashboard (status, token stream, analyst/reviewer panels, notifications).
- Settings management and persistence.

4. Hardening
- Offline/unstable network handling.
- Packaging and auto-update strategy.
- Observability, diagnostics, crash reporting.

## Dependencies
- Backend endpoints under `python/omnimind_backend/api` must remain stable.
- SSE event contracts must preserve field names and semantic ordering.

## Out of Scope (Current Step)
- This roadmap does not implement PySide6 UI code yet.
- It only defines the migration direction and required backend compatibility targets.
