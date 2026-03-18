from __future__ import annotations

import json

import pytest

from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.schemas.chat.agent import AgentChatRequest


class _NoisyToolGraph:
    async def astream_events(self, _graph_input, version: str = "v2"):
        assert version == "v2"
        yield {
            "event": "on_custom_event",
            "name": "tool_call_start",
            "data": {
                "tool": "read_file",
                "args": {"file_path": "/tmp/demo.py"},
                "tool_meta": {
                    "category": "filesystem",
                    "family": "filesystem",
                    "notifier_kind": "read_file",
                },
                "tool_call_id": "tc-noisy",
            },
        }
        yield {
            "event": "on_custom_event",
            "name": "tool_call",
            "data": {
                "tool": "read_file",
                "args": {"file_path": "/tmp/demo.py"},
                "tool_meta": {
                    "category": "filesystem",
                    "family": "filesystem",
                    "notifier_kind": "read_file",
                },
                "tool_call_id": "tc-noisy",
                "result_preview": '{"content":"print(1)"}',
            },
        }
        yield {"event": "on_custom_event", "name": "agent_response", "data": {"chunk": "ok"}}


@pytest.mark.asyncio
async def test_orchestrated_stream_filters_noisy_filesystem_notifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_save(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(AgentRuntime, "_save_message_bg", _noop_save)

    runtime = AgentRuntime()
    runtime._orchestrator_graph = _NoisyToolGraph()

    payload = AgentChatRequest(
        message="inspecione o arquivo",
        provider="openai",
        model="stub",
        orchestrate=True,
    )
    events = [event async for event in runtime.stream_chat(payload, session_id="session-noisy", run_id="run-noisy")]

    notifier_payloads = [json.loads(event.data) for event in events if event.type == "notifier"]
    tool_call_payloads = [json.loads(event.data) for event in events if event.type == "tool_call"]

    assert tool_call_payloads, events
    assert all(payload.get("kind") != "file_read" for payload in notifier_payloads)
    assert any(payload.get("name") == "read_file" for payload in tool_call_payloads)


def test_should_emit_backend_notifier_filters_operational_tool_noise() -> None:
    from mindflow_backend.runtime.streaming.notifier_policy import should_emit_backend_notifier

    assert should_emit_backend_notifier("gitnexus_query") is True
    assert should_emit_backend_notifier("context_loaded") is True
    assert should_emit_backend_notifier("file_read") is False
    assert should_emit_backend_notifier("file_write") is False
    assert should_emit_backend_notifier("shell_tab_exec") is False
    assert should_emit_backend_notifier("search_done") is False
    assert should_emit_backend_notifier("tool_start") is False
    assert should_emit_backend_notifier("performance_warning") is True
