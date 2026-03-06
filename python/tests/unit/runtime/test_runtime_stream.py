import json

import pytest

from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.schemas.agent import AgentChatRequest


class _DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _DummyModel:
    async def ainvoke(self, _messages):
        return _DummyResponse("Here is a deterministic response payload for streaming validation.")

    async def astream(self, _messages):
        class ChunkWithMetadata:
            def __init__(self, content, metadata=None):
                self.content = content
                self.response_metadata = metadata or {}

        yield ChunkWithMetadata("", {"thought": "I am thinking about this"})
        yield ChunkWithMetadata("Here ")
        yield ChunkWithMetadata("is ")
        yield ChunkWithMetadata("a deterministic response payload for streaming validation.")


class _ChunkWithThinkingList:
    def __init__(self) -> None:
        self.content = [
            {"type": "thinking", "thinking": "reasoning summary"},
            {"type": "text", "text": "final answer"},
        ]


class _DummyModelWithThinkingList:
    async def astream(self, _messages):
        yield _ChunkWithThinkingList()



@pytest.mark.asyncio
async def test_stream_contract_has_ordered_seq_and_run_linkage(monkeypatch) -> None:
    from unittest.mock import MagicMock
    monkeypatch.setattr("mindflow_backend.runtime.stream.db_session", MagicMock())
    monkeypatch.setattr("mindflow_backend.runtime.stream.ChatRepository", MagicMock())
    monkeypatch.setattr(
        "mindflow_backend.runtime.stream.get_model_for_provider",
        lambda _provider, _model: _DummyModel(),
    )

    runtime = AgentRuntime()
    payload = AgentChatRequest(message="summarize this", provider="openai", model="stub")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-1", run_id="run-1")]

    assert events
    filtered_events = [e for e in events if e.seq > 0 and e.seq < 999]
    assert [evt.seq for evt in filtered_events] == list(range(1, len(filtered_events) + 1))
    assert events[-1].type == "done"

    assert all(evt.meta is not None for evt in filtered_events)
    assert all(evt.meta and evt.meta.runId == "run-1" for evt in filtered_events)
    assert all(evt.meta and evt.meta.turnRunId == "session-1" for evt in filtered_events)

    response_events = [evt for evt in events if evt.type == "response"]
    assert response_events
    assert all(evt.meta and evt.meta.category is not None for evt in response_events)
    
    thought_events = [evt for evt in events if evt.type == "thought"]
    assert thought_events
    assert "I am thinking about this" in thought_events[0].data

    step_events = [evt for evt in events if evt.type == "agent_step"]
    assert step_events
    payload_data = json.loads(step_events[0].data)
    assert {"stepName", "detail", "action"}.issubset(set(payload_data.keys()))


@pytest.mark.asyncio
async def test_stream_contract_emits_tool_events_for_search(monkeypatch) -> None:
    monkeypatch.setattr(
        "mindflow_backend.runtime.stream.get_model_for_provider",
        lambda _provider, _model: _DummyModel(),
    )

    async def _fake_search(_query: str) -> str:
        return "fresh web context"

    monkeypatch.setattr("mindflow_backend.runtime.stream.search_web", _fake_search)

    runtime = AgentRuntime()
    payload = AgentChatRequest(message="search latest docs", provider="openai", model="stub")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-2", run_id="run-2")]

    assert any(evt.type == "tool_call" for evt in events)
    assert any(evt.type == "tool_result" for evt in events)


@pytest.mark.asyncio
async def test_stream_contract_extracts_thought_and_response_from_list_content(monkeypatch) -> None:
    from unittest.mock import MagicMock

    monkeypatch.setattr("mindflow_backend.runtime.stream.db_session", MagicMock())
    monkeypatch.setattr("mindflow_backend.runtime.stream.ChatRepository", MagicMock())
    monkeypatch.setattr(
        "mindflow_backend.runtime.stream.get_model_for_provider",
        lambda _provider, _model: _DummyModelWithThinkingList(),
    )

    runtime = AgentRuntime()
    payload = AgentChatRequest(message="responda", provider="openai", model="stub")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-3", run_id="run-3")]
    thought_events = [evt for evt in events if evt.type == "thought"]
    response_events = [evt for evt in events if evt.type == "response"]

    assert any("reasoning summary" in evt.data for evt in thought_events)
    assert any("final answer" in evt.data for evt in response_events)
