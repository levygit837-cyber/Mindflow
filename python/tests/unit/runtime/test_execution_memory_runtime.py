from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


class _DummyAsyncContext:
    async def __aenter__(self):
        return object(), object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@dataclass
class _FakeExecutionMemoryService:
    pause_requested: bool = False
    started: list[dict] = field(default_factory=list)
    resumed: list[str] = field(default_factory=list)
    status_updates: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    snapshots: list[dict] = field(default_factory=list)
    executions: dict[str, dict] = field(default_factory=dict)

    async def start_execution(self, **kwargs):
        execution_id = kwargs.get("execution_id") or "exec-1"
        record = {
            "id": execution_id,
            "session_id": kwargs["session_id"],
            "mode": kwargs["mode"],
            "status": "running",
            "provider": kwargs.get("provider"),
            "model": kwargs.get("model"),
            "metadata": kwargs.get("metadata", {}),
        }
        self.executions[execution_id] = record
        self.started.append(kwargs)
        return SimpleNamespace(**record)

    async def mark_status(self, execution_id: str, status: str, **kwargs):
        record = self.executions.setdefault(execution_id, {"id": execution_id})
        record["status"] = status
        record.update(kwargs)
        self.status_updates.append({"execution_id": execution_id, "status": status, **kwargs})
        return SimpleNamespace(**record)

    async def append_event(self, execution_id: str, event_type: str, payload: dict | None = None, **kwargs):
        self.events.append(
            {
                "execution_id": execution_id,
                "event_type": event_type,
                "payload": payload or {},
                **kwargs,
            }
        )

    async def create_snapshot(self, execution_id: str, **kwargs):
        snapshot = {"execution_id": execution_id, **kwargs}
        self.snapshots.append(snapshot)
        return SimpleNamespace(**snapshot)

    async def should_pause(self, execution_id: str) -> bool:
        return self.pause_requested

    async def request_pause(self, execution_id: str):
        self.pause_requested = True
        return await self.mark_status(execution_id, "pause_requested")

    async def get_execution(self, execution_id: str):
        record = self.executions.get(execution_id)
        return SimpleNamespace(**record) if record else None

    async def get_latest_snapshot(self, execution_id: str):
        for snapshot in reversed(self.snapshots):
            if snapshot["execution_id"] == execution_id:
                return SimpleNamespace(**snapshot)
        return None


class _SegmentedGraph:
    def __init__(self) -> None:
        self._segment = 0
        self.calls: list[dict] = []

    async def astream_events(self, graph_input, config=None, version: str = "v2"):
        self.calls.append({"input": graph_input, "config": config, "version": version})
        if self._segment == 0:
            self._segment += 1
            yield {"event": "on_chain_start", "name": "route", "data": {}}
            yield {"event": "on_chain_end", "name": "route", "data": {"output": {"decision": {"agent": "ORCHESTRATOR"}}}}
            return
        if self._segment == 1:
            self._segment += 1
            yield {"event": "on_custom_event", "name": "agent_response", "data": {"chunk": "final chunk"}}
            return

    async def aget_state(self, config):
        checkpoint_id = "cp-1" if self._segment == 1 else "cp-2"
        next_nodes = ("execute",) if self._segment == 1 else ()
        values = {"message": "resume me", "response": "final chunk" if not next_nodes else ""}
        return SimpleNamespace(
            values=values,
            next=next_nodes,
            config={"configurable": {"checkpoint_id": checkpoint_id, **(config or {}).get("configurable", {})}},
        )


@pytest.mark.asyncio
async def test_orchestrated_stream_pauses_at_safe_boundary_and_saves_snapshot(monkeypatch) -> None:
    from mindflow_backend.runtime.stream import AgentRuntime
    from mindflow_backend.schemas.agent import AgentChatRequest

    runtime = AgentRuntime()
    runtime._execution_memory = _FakeExecutionMemoryService(pause_requested=True)
    runtime._save_message_bg = AsyncMock()
    runtime._memory_service = None
    runtime._memory_publisher = None

    segmented_graph = _SegmentedGraph()

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream._load_history_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.get_settings",
        lambda: SimpleNamespace(default_provider="openai", default_model="gpt-test"),
    )
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.langgraph_memory",
        lambda: _DummyAsyncContext(),
        raising=False,
    )
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.build_simple_orchestrator_flow",
        lambda **_kwargs: segmented_graph,
        raising=False,
    )

    payload = AgentChatRequest(message="resume me", orchestrate=True, provider="openai", model="gpt-test")
    events = [event async for event in runtime.stream_chat(payload, session_id="sess-runtime", run_id="run-runtime")]

    assert segmented_graph.calls[0]["input"]["message"] == "resume me"
    assert any(evt.type == "notifier" and "execution_paused" in evt.data for evt in events)
    assert events[-1].type == "done"
    assert runtime._execution_memory.snapshots
    assert runtime._execution_memory.status_updates[-1]["status"] == "paused"


@pytest.mark.asyncio
async def test_resume_execution_continues_from_checkpoint(monkeypatch) -> None:
    from mindflow_backend.runtime.stream import AgentRuntime

    runtime = AgentRuntime()
    fake_execution_memory = _FakeExecutionMemoryService()
    fake_execution_memory.executions["exec-resume"] = {
        "id": "exec-resume",
        "session_id": "sess-runtime",
        "mode": "orchestrated",
        "status": "paused",
        "provider": "openai",
        "model": "gpt-test",
        "metadata": {
            "graph_input": {
                "message": "resume me",
                "provider": "openai",
                "model": "gpt-test",
                "session_id": "sess-runtime",
                "agent_type": None,
                "folder_path": None,
                "conversation_history": [],
            }
        },
    }
    runtime._execution_memory = fake_execution_memory
    runtime._save_message_bg = AsyncMock()
    runtime._memory_service = None
    runtime._memory_publisher = None

    segmented_graph = _SegmentedGraph()
    segmented_graph._segment = 1

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.langgraph_memory",
        lambda: _DummyAsyncContext(),
        raising=False,
    )
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.build_simple_orchestrator_flow",
        lambda **_kwargs: segmented_graph,
        raising=False,
    )

    events = [event async for event in runtime.resume_execution("exec-resume", run_id="run-resume")]

    assert segmented_graph.calls[0]["input"] is None
    assert any(evt.type == "response" and evt.data == "final chunk" for evt in events)
    assert fake_execution_memory.status_updates[-1]["status"] == "completed"
