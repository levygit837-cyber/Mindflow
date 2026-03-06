#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created python/.env from .env.example"
fi

docker compose --env-file .env -f docker-compose.backend.yml up -d

get_env_value() {
  local key="$1"
  local raw
  raw="$(grep -E "^${key}=" .env | tail -n 1 | cut -d '=' -f 2- || true)"
  printf '%s' "${raw}"
}

POSTGRES_CONTAINER_NAME="$(get_env_value POSTGRES_CONTAINER_NAME)"
POSTGRES_USER="$(get_env_value POSTGRES_USER)"
POSTGRES_DB="$(get_env_value POSTGRES_DB)"

POSTGRES_CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-mindflow-postgres-v1}"
POSTGRES_USER="${POSTGRES_USER:-mindflow_app}"
POSTGRES_DB="${POSTGRES_DB:-mindflow_v1}"

echo "Waiting for PostgreSQL container: ${POSTGRES_CONTAINER_NAME}"
for _ in $(seq 1 45); do
  if docker exec "${POSTGRES_CONTAINER_NAME}" pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    echo "PostgreSQL is ready."
    break
  fi
  sleep 1
done

if ! docker exec "${POSTGRES_CONTAINER_NAME}" pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
  echo "PostgreSQL did not become ready in time." >&2
  exit 1
fi

uv sync
uv run alembic upgrade head
uv run pytest -q

echo "Local stack is ready."
echo "Run API:      uv run mindflow-api"
echo "Run Desktop:  uv run mindflow-desktop"
