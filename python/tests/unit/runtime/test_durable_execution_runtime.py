from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest


@dataclass
class _FakeExecutionMemoryService:
    started: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    executions: dict[str, dict] = field(default_factory=dict)
    tree: dict | None = None
    snapshot: dict | None = None
    session_runtime_state: dict[str, dict] = field(default_factory=dict)

    async def start_execution(self, **kwargs):
        execution_id = kwargs.get("execution_id") or "exec-root"
        record = {
            "id": execution_id,
            "session_id": kwargs["session_id"],
            "root_execution_id": kwargs.get("root_execution_id") or execution_id,
            "parent_execution_id": kwargs.get("parent_execution_id"),
            "execution_role": kwargs.get("execution_role") or "root_orchestrator",
            "owner_execution_id": kwargs.get("owner_execution_id") or execution_id,
            "mode": kwargs.get("mode", "orchestrated"),
            "status": kwargs.get("status", "queued"),
            "current_stage": kwargs.get("stage", "routing"),
            "provider": kwargs.get("provider"),
            "model": kwargs.get("model"),
            "metadata": kwargs.get("metadata", {}),
        }
        self.executions[execution_id] = record
        self.started.append(kwargs)
        return SimpleNamespace(**record)

    async def get_execution(self, execution_id: str):
        record = self.executions.get(execution_id)
        return SimpleNamespace(**record) if record else None

    async def get_latest_snapshot(self, execution_id: str):
        if self.snapshot is None:
            return None
        return SimpleNamespace(**self.snapshot)

    async def get_execution_tree(self, execution_id: str):
        if self.tree is not None:
            return self.tree
        execution = self.executions[execution_id]
        return {
            "execution": execution,
            "messages": [],
            "processes": [],
            "children": [],
        }

    async def list_events(self, root_execution_id: str, after_id: int = 0):
        return [
            SimpleNamespace(**event)
            for event in self.events
            if event["payload"]["root_execution_id"] == root_execution_id and event["id"] > after_id
        ]

    async def list_messages(self, execution_id: str, include_consumed: bool = True):
        rows = [row for row in self.messages if row["execution_id"] == execution_id]
        if not include_consumed:
            rows = [row for row in rows if row["status"] == "pending"]
        return [SimpleNamespace(**row) for row in rows]

    async def list_processes(self, execution_id: str):
        return []

    async def record_message(self, **kwargs):
        message = {
            "id": len(self.messages) + 1,
            "sequence": len(self.messages) + 1,
            "status": kwargs.get("status", "pending"),
            "created_at": None,
            **kwargs,
        }
        self.messages.append(message)
        return SimpleNamespace(**message)

    async def append_event(self, execution_id: str, event_type: str, payload: dict | None = None, **kwargs):
        execution = self.executions[execution_id]
        event = {
            "id": len(self.events) + 1,
            "execution_id": execution_id,
            "sequence": len(self.events) + 1,
            "event_type": event_type,
            "message": kwargs.get("message"),
            "stage": kwargs.get("stage") or execution.get("current_stage"),
            "payload": {
                "execution_id": execution_id,
                "root_execution_id": execution.get("root_execution_id") or execution_id,
                "parent_execution_id": execution.get("parent_execution_id"),
                "agent": execution.get("agent_id"),
                "status": execution.get("status"),
                "stage": kwargs.get("stage") or execution.get("current_stage"),
                "progress": execution.get("progress"),
                "visibility": "internal",
                **(payload or {}),
            },
        }
        self.events.append(event)
        return SimpleNamespace(**event)

    async def save_session_runtime_state(self, *, session_id: str, execution_id: str | None = None, state: dict, version: int = 1):
        record = {
            "session_id": session_id,
            "execution_id": execution_id,
            "state_json": state,
            "version": version,
            "updated_at": None,
        }
        self.session_runtime_state[session_id] = record
        return SimpleNamespace(**record)


@pytest.mark.asyncio
async def test_create_execution_returns_root_status(monkeypatch) -> None:
    from mindflow_backend.runtime.stream import AgentRuntime
    from mindflow_backend.schemas.agent import AgentChatRequest

    runtime = AgentRuntime()
    runtime._execution_memory = _FakeExecutionMemoryService()

    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.get_settings",
        lambda: SimpleNamespace(default_provider="openai", default_model="gpt-test"),
    )

    payload = AgentChatRequest(message="durable orchestration", orchestrate=True, provider="openai", model="gpt-test")
    status = await runtime.create_execution(payload, session_id="sess-durable")

    assert status["execution_id"] == "exec-root"
    assert status["root_execution_id"] == "exec-root"
    assert status["stage"] == "routing"
    assert status["status"] == "queued"
    assert runtime._execution_memory.started[0]["status"] == "queued"
    assert runtime._execution_memory.started[0]["stage"] == "routing"
    assert runtime._execution_memory.session_runtime_state["sess-durable"]["execution_id"] == "exec-root"
    assert runtime._execution_memory.session_runtime_state["sess-durable"]["state_json"]["agent_runtime"]["root_execution_id"] == "exec-root"


@pytest.mark.asyncio
async def test_get_execution_status_includes_tree_and_events() -> None:
    from mindflow_backend.runtime.stream import AgentRuntime

    runtime = AgentRuntime()
    fake_execution_memory = _FakeExecutionMemoryService()
    fake_execution_memory.executions["exec-root"] = {
        "id": "exec-root",
        "session_id": "sess-durable",
        "root_execution_id": "exec-root",
        "parent_execution_id": None,
        "execution_role": "root_orchestrator",
        "owner_execution_id": "exec-root",
        "mode": "orchestrated",
        "status": "running",
        "current_stage": "reflecting",
        "provider": "openai",
        "model": "gpt-test",
        "metadata": {"graph_input": {"message": "durable orchestration"}},
        "progress": 0.6,
    }
    fake_execution_memory.tree = {
        "execution": {"id": "exec-root", "status": "running"},
        "messages": [],
        "processes": [],
        "children": [
            {
                "execution": {"id": "exec-child", "status": "running"},
                "messages": [{"content": "partial update"}],
                "processes": [{"pid": 4242}],
                "children": [],
            }
        ],
    }
    fake_execution_memory.snapshot = {"context_json": {"summary": "checkpoint"}}
    fake_execution_memory.events = [
        {
            "id": 1,
            "execution_id": "exec-root",
            "sequence": 1,
            "event_type": "execution_started",
            "message": None,
            "stage": "routing",
            "payload": {"root_execution_id": "exec-root"},
        }
    ]
    runtime._execution_memory = fake_execution_memory

    status = await runtime.get_execution_status("exec-root")

    assert status["stage"] == "reflecting"
    assert status["tree"]["children"][0]["execution"]["id"] == "exec-child"
    assert status["events"][0]["event_type"] == "execution_started"
    assert status["snapshot"] == {"summary": "checkpoint"}


@pytest.mark.asyncio
async def test_send_execution_message_records_context_update() -> None:
    from mindflow_backend.runtime.stream import AgentRuntime

    runtime = AgentRuntime()
    fake_execution_memory = _FakeExecutionMemoryService()
    fake_execution_memory.executions["exec-child"] = {
        "id": "exec-child",
        "session_id": "sess-durable",
        "root_execution_id": "exec-root",
        "parent_execution_id": "exec-root",
        "execution_role": "delegated_agent",
        "owner_execution_id": "exec-root",
        "mode": "orchestrated",
        "status": "running",
        "current_stage": "working",
        "agent_id": "coder",
        "metadata": {},
    }
    runtime._execution_memory = fake_execution_memory

    result = await runtime.send_execution_message(
        "exec-child",
        message_type="context_update",
        content="Use o contexto mais recente",
        sender_execution_id="exec-root",
    )

    assert result["message"]["message_type"] == "context_update"
    assert result["message"]["recipient_execution_id"] == "exec-child"
    assert fake_execution_memory.messages[0]["content"] == "Use o contexto mais recente"
    assert fake_execution_memory.session_runtime_state["sess-durable"]["execution_id"] == "exec-root"
    assert fake_execution_memory.events[0]["event_type"] == "message_received"
