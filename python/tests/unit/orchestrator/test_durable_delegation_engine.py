from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest


@dataclass
class _FakeExecutionMemoryService:
    started: list[dict] = field(default_factory=list)
    status_updates: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)

    async def start_execution(self, **kwargs):
        self.started.append(kwargs)
        return SimpleNamespace(
            id=kwargs.get("execution_id", "exec-child"),
            root_execution_id=kwargs.get("root_execution_id"),
            parent_execution_id=kwargs.get("parent_execution_id"),
            current_stage=kwargs.get("stage", "booting"),
            status=kwargs.get("status", "running"),
        )

    async def mark_status(self, execution_id: str, status: str, **kwargs):
        self.status_updates.append({"execution_id": execution_id, "status": status, **kwargs})
        return SimpleNamespace(id=execution_id, status=status, current_stage=kwargs.get("stage"))

    async def append_event(self, execution_id: str, event_type: str, payload: dict | None = None, **kwargs):
        self.events.append(
            {
                "execution_id": execution_id,
                "event_type": event_type,
                "payload": payload or {},
                **kwargs,
            }
        )

    async def record_message(self, **kwargs):
        message = {"id": len(self.messages) + 1, **kwargs}
        self.messages.append(message)
        return SimpleNamespace(**message)

    async def consume_pending_messages(self, execution_id: str):
        return []


class _FakeLLM:
    def bind_tools(self, _tools):
        return self

    async def ainvoke(self, messages):
        return SimpleNamespace(content="agent output ready", tool_calls=[])


@pytest.mark.asyncio
async def test_delegate_task_creates_child_execution_and_final_result(monkeypatch) -> None:
    from mindflow_backend.orchestrator.delegation.engine import DelegationEngine
    from mindflow_backend.schemas.orchestration.delegation import DelegationTask, OrchestratorSession
    from mindflow_backend.schemas.orchestration.orchestrator import AgentType

    fake_execution_memory = _FakeExecutionMemoryService()

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.delegation.engine.get_agent",
        lambda *args, **kwargs: SimpleNamespace(
            system_prompt="You are a delegated coder.",
            sandbox="none",
            agent_id="coder",
        ),
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.delegation.engine.get_model_for_provider",
        lambda *args, **kwargs: _FakeLLM(),
    )

    engine = DelegationEngine(execution_memory=fake_execution_memory)
    task = DelegationTask(
        agent=AgentType.CODER,
        objective="Inspect the working tree",
        expected_output="Return a concise summary",
        max_iterations=2,
    )

    result = await engine.delegate_task(
        task,
        OrchestratorSession(),
        session_id="sess-durable",
        root_execution_id="exec-root",
        parent_execution_id="exec-root",
    )

    assert result.status == "completed"
    assert fake_execution_memory.started[0]["root_execution_id"] == "exec-root"
    assert fake_execution_memory.started[0]["parent_execution_id"] == "exec-root"
    assert fake_execution_memory.started[0]["execution_role"] == "delegated_agent"
    assert any(event["event_type"] == "delegation_started" for event in fake_execution_memory.events)
    assert fake_execution_memory.messages[0]["message_type"] == "final_result"
    assert fake_execution_memory.messages[0]["recipient_execution_id"] == "exec-root"
