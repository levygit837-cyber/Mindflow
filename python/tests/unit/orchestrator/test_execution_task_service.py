from __future__ import annotations

import pytest


class _FakeSessionRuntimeStateService:
    def __init__(self) -> None:
        self.saved: dict[str, dict] = {}

    async def save_session_state(self, session_id: str, state: dict) -> dict:
        self.saved[session_id] = state
        return state

    async def load_session_state(self, session_id: str) -> dict | None:
        return self.saved.get(session_id)

    async def list_session_states(self) -> list[dict]:
        return [
            {"session_id": session_id, **state}
            for session_id, state in self.saved.items()
        ]


@pytest.mark.asyncio
async def test_execution_task_service_persists_and_rehydrates_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mindflow_backend.services.orchestration.execution_task_service as module
    from mindflow_backend.services.orchestration.execution_task_service import (
        ExecutionTaskService,
    )

    fake_runtime_state = _FakeSessionRuntimeStateService()
    monkeypatch.setattr(
        module,
        "_get_session_runtime_state_service",
        lambda: fake_runtime_state,
        raising=False,
    )

    service = ExecutionTaskService()
    started = await service.start_execution(
        session_id="persisted-session",
        task_id="persisted-task",
        item_id="item-1",
        execution_key="item:item-1",
        execution_type="agent_step",
        description="Resolve first item",
        metadata={"source": "test"},
    )
    await service.append_output(
        session_id="persisted-session",
        execution_task_id=started.execution_task_id,
        chunk="resolver started",
    )
    cancel_result = await service.request_task_cancellation(
        session_id="persisted-session",
        task_id="persisted-task",
        reason="Stop current execution",
    )

    persisted_task = fake_runtime_state.saved["persisted-session"]["execution_tasks"]["tasks"][
        "persisted-task"
    ]
    assert cancel_result["killed_executions"] == 1
    assert (
        persisted_task["executions"][started.execution_task_id]["output"] == ["resolver started"]
    )
    assert persisted_task["control"]["cancel_requested"] is True

    restored_service = ExecutionTaskService()
    monkeypatch.setattr(
        module,
        "_get_session_runtime_state_service",
        lambda: fake_runtime_state,
        raising=False,
    )

    executions = await restored_service.list_task_executions_by_task_id("persisted-task")
    overview = await restored_service.get_task_overview("persisted-task")

    assert len(executions) == 1
    assert executions[0].status == "killed"
    assert overview["status"] == "cancelling"
    assert overview["cancel_requested"] is True


@pytest.mark.asyncio
async def test_execution_task_service_preserves_killed_terminal_status() -> None:
    from mindflow_backend.services.orchestration.execution_task_service import (
        ExecutionTaskService,
    )

    service = ExecutionTaskService()
    started = await service.start_execution(
        session_id="kill-session",
        task_id="kill-task",
        item_id="item-1",
        execution_key="item:item-1",
        execution_type="agent_step",
        description="Resolve item",
    )
    await service.kill_execution(
        session_id="kill-session",
        execution_task_id=started.execution_task_id,
        reason="User requested stop",
    )
    completed = await service.complete_execution(
        session_id="kill-session",
        execution_task_id=started.execution_task_id,
        metadata={"late_result": True},
    )

    assert completed.status == "killed"
    assert completed.error == "User requested stop"
