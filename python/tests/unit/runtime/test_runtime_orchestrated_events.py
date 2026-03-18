import contextlib
import json

import pytest

from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.schemas.agent import AgentChatRequest


class _FakeGraph:
    async def astream_events(self, _graph_input, version: str = "v2"):
        assert version == "v2"
        yield {"event": "on_custom_event", "name": "dt_step", "data": {"task": "plan", "status": "resolving"}}
        yield {"event": "on_custom_event", "name": "agent_tool_call", "data": {"chunk": {"name": "search_web"}}}
        yield {"event": "on_custom_event", "name": "agent_response", "data": {"chunk": "ok"}}


@pytest.mark.asyncio
async def test_orchestrated_stream_maps_dt_step_and_tool_call_without_crashing(monkeypatch) -> None:
    monkeypatch.setattr("mindflow_backend.runtime.stream.db_session", lambda: contextlib.nullcontext(None))

    runtime = AgentRuntime()
    runtime._orchestrator_graph = _FakeGraph()

    payload = AgentChatRequest(
        message="oi",
        provider="openai",
        model="stub",
        orchestrate=True,
    )
    events = [event async for event in runtime.stream_chat(payload, session_id="session-orch", run_id="run-orch")]

    assert events[-1].type == "done"
    assert not any(evt.type == "error" for evt in events)

    step_payloads = [json.loads(evt.data) for evt in events if evt.type == "agent_step"]
    assert any(p.get("stepName") == "DT: plan" for p in step_payloads)

    # tool calls no longer emit a thought event; search_done is suppressed by notifier_policy
    # asserting no error confirms agent_tool_call was processed without crashing
