from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import httpx
import pytest

from mindflow_backend.schemas.agent import StreamEvent


def _live_enabled() -> bool:
    return os.getenv("RUN_LIVE_VERTEX_TESTS", "").strip() == "1"


async def _iter_sse_payloads(lines: AsyncIterator[str]) -> AsyncIterator[str]:
    data_lines: list[str] = []
    async for line in lines:
        if not line:
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        yield "\n".join(data_lines)


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_LIVE_VERTEX_TESTS=1 to run live Vertex validation")
async def test_live_vertex_stream_returns_model_thought_and_response() -> None:
    base_url = os.getenv("MINDFLOW_API_URL", "http://127.0.0.1:8000").rstrip("/")
    payload = {
        "message": "Explique em duas frases por que testes de integração importam.",
        "provider": "vertexai",
        "model": "gemini-3-flash-preview",
        "agent_type": "coder",
        "orchestrate": False,
    }

    events: list[StreamEvent] = []
    async with httpx.AsyncClient(timeout=120.0) as client, client.stream(
        "POST",
        f"{base_url}/v1/agent/chat/stream",
        json=payload,
        headers={"Accept": "text/event-stream"},
    ) as response:
        response.raise_for_status()
        async for payload_json in _iter_sse_payloads(response.aiter_lines()):
            try:
                raw = json.loads(payload_json)
            except json.JSONDecodeError:
                continue
            events.append(StreamEvent.model_validate(raw))
            if events[-1].type == "done":
                break

    thought_count = sum(1 for e in events if e.type == "thought")
    response_count = sum(1 for e in events if e.type == "response")
    done_count = sum(1 for e in events if e.type == "done")

    assert thought_count >= 1, f"expected thought>=1, got {thought_count}"
    assert response_count >= 1, f"expected response>=1, got {response_count}"
    assert done_count >= 1, f"expected done>=1, got {done_count}"
