# OmniMind Python Runtime (v1)

Agent-only backend + PySide6/QML desktop frontend.

## Stack
- FastAPI (`/v1/*`)
- PostgreSQL + SQLAlchemy + Alembic
- Redis + RQ (optional background worker)
- LangChain provider adapters
- PySide6/QML desktop (`omnimind_desktop`)

## Engineering Standards
- Arquitetura e convenções oficiais: `docs/architecture/python-engineering-standards.md`
- Registro de decisões estruturais: `docs/adr/`

Comandos padronizados de qualidade:
```bash
cd python
make check
```

Ou individualmente:
```bash
cd python
make format
make lint
make typecheck
make test
```

Padronização de commit:
- `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

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

## One-Command Desktop Launcher (Recommended)
`omnimind-desktop` now boots required local services before opening the UI:
- Docker infra (`postgres` + `redis`)
- DB migrations (`alembic upgrade head`)
- local API server

Use either command:
```bash
cd python
uv run omnimind-desktop
# or
./scripts/start_desktop_stack.sh
```

Optional env flags (in `python/.env` or shell):
- `OMNIMIND_START_GRPC=1` to also start gRPC server
- `OMNIMIND_START_WORKER=1` to also start worker
- `OMNIMIND_DESKTOP_SKIP_UI=1` to run bootstrap only (no UI)

Logs:
- `python/.logs/api.log`
- `python/.logs/grpc.log` (if enabled)
- `python/.logs/worker.log` (if enabled)

## Fresh Local DB (New Credentials)
Use a fresh Postgres + Redis stack with dedicated credentials and ports:

```bash
cd python
cp .env.example .env
./scripts/setup_local_stack.sh
```

Default local credentials in `.env.example`:
- Postgres container: `omnimind-postgres-v1`
- DB: `omnimind_v1`
- User: `omnimind_app`
- Password: `omnimind_dev_local_2026`
- Port: `5433`
- Redis port: `6380`

After setup:
```bash
cd python
uv run omnimind-api
# new terminal
cd python
uv run omnimind-desktop
```

Health check:
```bash
curl http://127.0.0.1:8000/health
```

## Local Swarm Backup (before removal)
```bash
cd python
uv run scripts/backup_swarm_data.py
# or
./scripts/backup_swarm_data.sh
```

Artifacts are generated in `backups/swarm/<timestamp>/`.
