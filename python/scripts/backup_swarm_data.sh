#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uv run scripts/backup_swarm_data.py "$@"
