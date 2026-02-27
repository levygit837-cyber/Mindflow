#!/usr/bin/env python3
"""Export local backup artifacts for Swarm tables.

Artifacts:
- swarm_tasks.jsonl
- swarm_events.jsonl
- swarm.sql
- manifest.json (checksums + row counts)
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from omnimind_backend.infra.config import get_settings


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return str(value)


def _to_sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        escaped = json.dumps(value, ensure_ascii=False).replace("'", "''")
        return f"'{escaped}'::jsonb"
    if isinstance(value, datetime):
        return f"'{value.isoformat()}'::timestamptz"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, default=_json_default, ensure_ascii=False) + "\n")


def _write_sql(path: Path, tasks: list[dict[str, Any]], events: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("-- OmniMind local Swarm backup\n")
        fh.write(f"-- generated_at: {_iso_now()}\n\n")
        fh.write("BEGIN;\n\n")

        fh.write(
            "CREATE TABLE IF NOT EXISTS swarm_tasks (\n"
            "  task_id VARCHAR(64) PRIMARY KEY,\n"
            "  description TEXT NOT NULL,\n"
            "  provider VARCHAR(64) NOT NULL,\n"
            "  model VARCHAR(128) NOT NULL,\n"
            "  working_path TEXT,\n"
            "  status VARCHAR(32) NOT NULL,\n"
            "  coder_plan TEXT,\n"
            "  analyst_state VARCHAR(32) NOT NULL,\n"
            "  sandbox_display TEXT NOT NULL,\n"
            "  reviewer_report_md TEXT NOT NULL,\n"
            "  error_message TEXT,\n"
            "  started_at TIMESTAMPTZ NOT NULL,\n"
            "  updated_at TIMESTAMPTZ NOT NULL,\n"
            "  completed_at TIMESTAMPTZ\n"
            ");\n\n"
        )

        fh.write(
            "CREATE TABLE IF NOT EXISTS swarm_events (\n"
            "  id INTEGER PRIMARY KEY,\n"
            "  event_id VARCHAR(64) NOT NULL UNIQUE,\n"
            "  task_id VARCHAR(64) NOT NULL,\n"
            "  sequence_number INTEGER NOT NULL,\n"
            "  event_type VARCHAR(64) NOT NULL,\n"
            "  agent_id VARCHAR(64) NOT NULL,\n"
            "  timestamp TIMESTAMPTZ NOT NULL,\n"
            "  payload JSONB NOT NULL\n"
            ");\n\n"
        )

        if tasks:
            columns = list(tasks[0].keys())
            fh.write(f"TRUNCATE TABLE swarm_tasks;\n")
            for row in tasks:
                values = ", ".join(_to_sql_literal(row.get(col)) for col in columns)
                fh.write(
                    f"INSERT INTO swarm_tasks ({', '.join(columns)}) VALUES ({values});\n"
                )
            fh.write("\n")

        if events:
            columns = list(events[0].keys())
            fh.write(f"TRUNCATE TABLE swarm_events;\n")
            for row in events:
                values = ", ".join(_to_sql_literal(row.get(col)) for col in columns)
                fh.write(
                    f"INSERT INTO swarm_events ({', '.join(columns)}) VALUES ({values});\n"
                )
            fh.write("\n")

        fh.write("COMMIT;\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    timestamp = _iso_now()
    output_dir = Path(args.output_dir) if args.output_dir else Path("backups/swarm") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks_rows: list[dict[str, Any]] = []
    events_rows: list[dict[str, Any]] = []

    with engine.connect() as conn:
        table_names = set(
            row[0]
            for row in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            ).all()
        )

        if "swarm_tasks" in table_names:
            tasks_rows = [dict(row) for row in conn.execute(text("SELECT * FROM swarm_tasks ORDER BY task_id")).mappings().all()]
        if "swarm_events" in table_names:
            events_rows = [
                dict(row)
                for row in conn.execute(text("SELECT * FROM swarm_events ORDER BY id")).mappings().all()
            ]

    tasks_jsonl = output_dir / "swarm_tasks.jsonl"
    events_jsonl = output_dir / "swarm_events.jsonl"
    sql_path = output_dir / "swarm.sql"

    _write_jsonl(tasks_jsonl, tasks_rows)
    _write_jsonl(events_jsonl, events_rows)
    _write_sql(sql_path, tasks_rows, events_rows)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "databaseUrl": "<redacted>",
        "tables": {
            "swarm_tasks": {"rows": len(tasks_rows)},
            "swarm_events": {"rows": len(events_rows)},
        },
        "files": {
            tasks_jsonl.name: {"sha256": _sha256(tasks_jsonl), "bytes": tasks_jsonl.stat().st_size},
            events_jsonl.name: {"sha256": _sha256(events_jsonl), "bytes": events_jsonl.stat().st_size},
            sql_path.name: {"sha256": _sha256(sql_path), "bytes": sql_path.stat().st_size},
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(str(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
