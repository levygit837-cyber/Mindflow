#!/usr/bin/env python3
"""Benchmark the agent transport (local vs network) before switching the default.

Output contract (stable JSON schema):
{
  "transport": "local|network",
  "requests": 25,
  "success_rate": 1.0,
  "ttfb_ms": {"p50": 0, "p95": 0, "p99": 0},
  "total_latency_ms": {"p50": 0, "p95": 0, "p99": 0},
  "events_per_stream": {"p50": 0, "p95": 0},
  "errors": []
}

Usage:
    cd python
    uv run python scripts/benchmark_agent_transport.py \\
        --transport local --requests 10 --message "ping" \\
        --output ../output/grpc-local-baseline.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path


def _percentile(data: list[float], pct: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


async def _run_single(client, message: str, session_id: str) -> dict:
    """Run one stream and return timing + event count."""
    result: dict = {"ok": False, "ttfb_ms": 0.0, "total_ms": 0.0, "events": 0, "error": ""}
    t0 = time.monotonic()
    try:
        first = True
        async for _event in client.stream_chat(
            session_id=session_id,
            message=message,
        ):
            if first:
                result["ttfb_ms"] = (time.monotonic() - t0) * 1000
                first = False
            result["events"] += 1
        result["total_ms"] = (time.monotonic() - t0) * 1000
        result["ok"] = True
    except Exception as exc:
        result["error"] = str(exc)
        result["total_ms"] = (time.monotonic() - t0) * 1000
    return result


async def run_benchmark(transport: str, n_requests: int, message: str) -> dict:
    """Run the full benchmark and return the report dict."""
    from mindflow_backend.grpc.factory import get_runtime_client

    client = get_runtime_client(mode=transport)

    ttfb_list: list[float] = []
    total_list: list[float] = []
    events_list: list[int] = []
    errors: list[str] = []

    for i in range(n_requests):
        session_id = f"bench-{uuid.uuid4()}"
        res = await _run_single(client, message, session_id)
        if res["ok"]:
            ttfb_list.append(res["ttfb_ms"])
            total_list.append(res["total_ms"])
            events_list.append(res["events"])
        else:
            errors.append(res["error"])

    success_count = n_requests - len(errors)
    return {
        "transport": transport,
        "requests": n_requests,
        "success_rate": success_count / n_requests if n_requests else 0.0,
        "ttfb_ms": {
            "p50": _percentile(ttfb_list, 50),
            "p95": _percentile(ttfb_list, 95),
            "p99": _percentile(ttfb_list, 99),
        },
        "total_latency_ms": {
            "p50": _percentile(total_list, 50),
            "p95": _percentile(total_list, 95),
            "p99": _percentile(total_list, 99),
        },
        "events_per_stream": {
            "p50": _percentile([float(e) for e in events_list], 50),
            "p95": _percentile([float(e) for e in events_list], 95),
        },
        "errors": errors[:20],  # cap at 20 for readability
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark agent transport")
    parser.add_argument("--transport", choices=["local", "network", "auto"], default="local")
    parser.add_argument("--requests", type=int, default=25)
    parser.add_argument("--message", default="ping")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    report = asyncio.run(run_benchmark(args.transport, args.requests, args.message))

    json_out = json.dumps(report, indent=2)
    print(json_out)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_out)
        print(f"\nReport written to {out_path}", file=sys.stderr)

    if report["success_rate"] < 1.0:
        sys.exit(1)


if __name__ == "__main__":
    main()
