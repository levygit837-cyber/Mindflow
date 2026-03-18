from __future__ import annotations

import json

import pytest

from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.schemas.chat.agent import AgentChatRequest


class _FakeGraph:
    async def astream_events(self, _graph_input, version: str = "v2"):
        assert version == "v2"
        yield {
            "event": "on_custom_event",
            "name": "tool_call_start",
            "data": {
                "tool": "gitnexus_context",
                "args": {"name": "AgentRuntime"},
                "tool_meta": {
                    "category": "code_analysis",
                    "family": "gitnexus",
                    "notifier_kind": "gitnexus_context",
                },
                "tool_call_id": "tc-1",
            },
        }
        yield {
            "event": "on_custom_event",
            "name": "tool_call",
            "data": {
                "tool": "gitnexus_context",
                "args": {"name": "AgentRuntime"},
                "tool_meta": {
                    "category": "code_analysis",
                    "family": "gitnexus",
                    "notifier_kind": "gitnexus_context",
                },
                "tool_call_id": "tc-1",
                "result_preview": '{"status":"ok"}',
            },
        }
        yield {"event": "on_custom_event", "name": "agent_response", "data": {"chunk": "ok"}}


@pytest.mark.asyncio
async def test_orchestrated_stream_emits_gitnexus_notifier(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_save(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(AgentRuntime, "_save_message_bg", _noop_save)

    runtime = AgentRuntime()
    runtime._orchestrator_graph = _FakeGraph()

    payload = AgentChatRequest(
        message="mapear contexto do runtime",
        provider="openai",
        model="stub",
        orchestrate=True,
    )
    events = [event async for event in runtime.stream_chat(payload, session_id="session-orch", run_id="run-orch")]

    notifier_payloads = [json.loads(event.data) for event in events if event.type == "notifier"]
    tool_call_payloads = [json.loads(event.data) for event in events if event.type == "tool_call"]

    assert any(payload.get("kind") == "gitnexus_context" for payload in notifier_payloads)
    assert any(payload.get("tool_meta", {}).get("family") == "gitnexus" for payload in tool_call_payloads)
    assert events[-1].type == "done"
