# OmniMind Python Runtime (v1)

Agent-only backend + terminal-first CLI + PySide6/QML desktop frontend (legacy).

## Stack
- FastAPI (`/v1/*`)
- PostgreSQL + SQLAlchemy + Alembic
- Redis + RQ (optional background worker)
- LangChain provider adapters
- Typer + Rich CLI (`omnimind_cli`)
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

## Run
```bash
cd python
uv sync
uv run alembic upgrade head
uv run omnimind-api
```

Terminal-first CLI:
```bash
cd python
uv run omnimind-cli health
uv run omnimind-cli chat -m "Explique o estado atual do runtime"
# chat interativo com conexao inicial e loop de conversa
uv run omnimind-cli connect --provider vertexai --model gemini-3-flash-preview
# com override de provider/model
uv run omnimind-cli chat -m "hello" --provider vertexai --model gemini-3-flash-preview
# workflow (atalho para execução com stream)
uv run omnimind-cli workflow run -m "planeje os próximos passos"
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
