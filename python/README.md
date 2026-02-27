# OmniMind Python Runtime (v1)

Agent-only backend + PySide6/QML desktop frontend.

## Stack
- FastAPI (`/v1/*`)
- PostgreSQL + SQLAlchemy + Alembic
- Redis + RQ (optional background worker)
- LangChain provider adapters
- PySide6/QML desktop (`omnimind_desktop`)

## API Surface (v1)
- `POST /v1/agent/chat/stream`
- `GET /v1/agent/sessions`
- `POST /v1/agent/sessions`
- `PATCH /v1/agent/sessions/{session_id}`
- `DELETE /v1/agent/sessions/{session_id}`
- `GET /v1/agent/sessions/{session_id}/messages`
- `GET /v1/agent/sessions/{session_id}/runs`
- `GET /v1/agent/mind/allowlist`
- `GET /v1/agent/mind/projects`
- `POST /v1/agent/mind/projects`
- `GET /v1/agent/mind/sessions?folderPath=...`
- `GET /v1/agent/mind/links?folderPath=...`
- `POST /v1/agent/mind/links`
- `DELETE /v1/agent/mind/links/{id}`
- `POST /v1/agent/mind/jobs`
- `GET /v1/agent/mind/jobs/{job_id}`
- `POST /v1/agent/mind/sandbox/query`

## Run
```bash
cd python
uv sync
uv run alembic upgrade head
uv run omnimind-api
```

Desktop app:
```bash
cd python
uv run omnimind-desktop
```

## Local Swarm Backup (before removal)
```bash
cd python
uv run scripts/backup_swarm_data.py
# or
./scripts/backup_swarm_data.sh
```

Artifacts are generated in `backups/swarm/<timestamp>/`.
