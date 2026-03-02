from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from omnimind_backend.schemas.agent import StreamEvent
from omnimind_cli.sse import iter_sse_payloads


def _wait_for_health(base_url: str, attempts: int = 20, sleep_seconds: float = 1.5) -> dict[str, Any]:
    last_error: str | None = None
    for _ in range(attempts):
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{base_url}/health")
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict) and payload.get("status") == "ok":
                    return payload
                last_error = f"Unexpected health payload: {payload}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(sleep_seconds)
    raise RuntimeError(f"Backend health check failed after {attempts} attempts: {last_error}")


def _collect_stream_events(base_url: str, payload: dict[str, Any]) -> list[StreamEvent]:
    events: list[StreamEvent] = []
    with (
        httpx.Client(timeout=120.0) as client,
        client.stream(
            "POST",
            f"{base_url}/v1/agent/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response,
    ):
        response.raise_for_status()
        for payload_json in iter_sse_payloads(response.iter_lines()):
            try:
                raw = json.loads(payload_json)
            except json.JSONDecodeError:
                continue
            event = StreamEvent.model_validate(raw)
            events.append(event)
            if event.type == "done":
                break
    return events


def _persist_report(report: dict[str, Any], logs_dir: Path) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = logs_dir / f"vertex_stream_verify_{timestamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Vertex stream emits thought, response and done events.")
    parser.add_argument("--base-url", default=os.getenv("OMNIMIND_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--provider", default="vertexai")
    parser.add_argument("--model", default="gemini-3-flash-preview")
    parser.add_argument("--agent-type", default="coder")
    parser.add_argument("--message", default="Explique em duas frases por que testes de integração importam.")
    parser.add_argument("--logs-dir", default=".logs")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    payload = {
        "message": args.message,
        "provider": args.provider,
        "model": args.model,
        "agent_type": args.agent_type,
        "orchestrate": False,
    }

    _wait_for_health(base_url)
    events = _collect_stream_events(base_url, payload)

    thought_count = sum(1 for e in events if e.type == "thought")
    response_count = sum(1 for e in events if e.type == "response")
    done_count = sum(1 for e in events if e.type == "done")
    event_types = [e.type for e in events]

    passed = thought_count >= 1 and response_count >= 1 and done_count == 1
    report = {
        "base_url": base_url,
        "payload": payload,
        "summary": {
            "thought_count": thought_count,
            "response_count": response_count,
            "done_count": done_count,
            "passed": passed,
        },
        "event_types": event_types,
        "event_count": len(events),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    report_path = _persist_report(report, Path(args.logs_dir))

    if passed:
        print("PASS: thought>=1, response>=1, done==1")
        print(f"Report: {report_path}")
        return 0

    print("FAIL: expected thought>=1, response>=1, done==1")
    print(json.dumps(report["summary"], ensure_ascii=True))
    print(f"Report: {report_path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
