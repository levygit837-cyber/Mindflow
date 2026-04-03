from __future__ import annotations

import asyncio
from datetime import timedelta

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
async def test_todo_planning_service_replace_focus_and_stale() -> None:
    from mindflow_backend.services.orchestration.todo_planning_service import TodoPlanningService

    service = TodoPlanningService(stale_after=timedelta(milliseconds=1))
    session_id = "todo-session"
    task_id = "task-alpha"

    snapshot = await service.replace_list(
        session_id=session_id,
        task_id=task_id,
        goal="Ship todo planning",
        source="planner",
        items=[
            {
                "item_id": "t1",
                "title": "Map orchestration hooks",
                "description": "Inspect planner and decomposition flows",
                "owner_agent": "analyst",
                "priority": "medium",
                "dependencies": [],
                "complexity_score": 0.35,
            },
            {
                "item_id": "t2",
                "title": "Implement service",
                "description": "Create planning service and registry integration",
                "owner_agent": "coder",
                "priority": "high",
                "dependencies": ["t1"],
                "complexity_score": 0.6,
            },
        ],
    )

    assert snapshot.todo_list.task_id == task_id
    assert snapshot.summary.total_items == 2
    assert snapshot.summary.open_items == 2

    focused = await service.focus_complex_items(session_id=session_id, task_id=task_id, limit=2)
    assert [item.item_id for item in focused.items] == ["t2", "t1"]

    updated = await service.update_item_status(
        session_id=session_id,
        task_id=task_id,
        item_id="t2",
        status="completed",
        notes="Done",
    )
    assert updated.summary.completed_items == 1

    await asyncio.sleep(0.01)
    assert await service.is_stale(session_id=session_id, task_id=task_id) is True


@pytest.mark.asyncio
async def test_todo_planning_service_isolated_by_session_and_task() -> None:
    from mindflow_backend.services.orchestration.todo_planning_service import TodoPlanningService

    service = TodoPlanningService()

    await service.replace_list(
        session_id="session-a",
        task_id="task-1",
        goal="A",
        source="planner",
        items=[{"item_id": "a1", "title": "A1"}],
    )
    await service.replace_list(
        session_id="session-a",
        task_id="task-2",
        goal="B",
        source="planner",
        items=[{"item_id": "b1", "title": "B1"}],
    )
    await service.replace_list(
        session_id="session-b",
        task_id="task-1",
        goal="C",
        source="planner",
        items=[{"item_id": "c1", "title": "C1"}],
    )

    session_a = await service.get_session_lists("session-a")
    session_b = await service.get_session_lists("session-b")

    assert {summary.task_id for summary in session_a} == {"task-1", "task-2"}
    assert {summary.task_id for summary in session_b} == {"task-1"}

    task_lookup = await service.get_list_by_task_id("task-2")
    assert task_lookup.todo_list.goal == "B"


@pytest.mark.asyncio
async def test_todo_planning_service_persists_and_rehydrates_state(monkeypatch: pytest.MonkeyPatch) -> None:
    import mindflow_backend.services.orchestration.todo_planning_service as module
    from mindflow_backend.services.orchestration.todo_planning_service import TodoPlanningService

    fake_runtime_state = _FakeSessionRuntimeStateService()
    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: fake_runtime_state, raising=False)

    first_service = TodoPlanningService()
    await first_service.replace_list(
        session_id="persisted-session",
        task_id="persisted-task",
        goal="Persist todo state",
        source="planner",
        items=[
            {
                "item_id": "one",
                "title": "Capture snapshot",
                "status": "in_progress",
                "complexity_score": 0.4,
            }
        ],
    )

    assert fake_runtime_state.saved["persisted-session"]["todo_planning"]["tasks"]["persisted-task"]["todo_list"]["goal"] == "Persist todo state"

    second_service = TodoPlanningService()
    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: fake_runtime_state, raising=False)

    restored = await second_service.get_list(session_id="persisted-session", task_id="persisted-task")

    assert restored.todo_list.goal == "Persist todo state"
    assert restored.todo_list.items[0].title == "Capture snapshot"


@pytest.mark.asyncio
async def test_todo_planning_service_persists_item_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    import mindflow_backend.services.orchestration.todo_planning_service as module
    from mindflow_backend.services.orchestration.todo_planning_service import TodoPlanningService

    fake_runtime_state = _FakeSessionRuntimeStateService()
    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: fake_runtime_state, raising=False)

    service = TodoPlanningService()
    await service.replace_list(
        session_id="update-session",
        task_id="update-task",
        goal="Persist task updates",
        source="planner",
        items=[
            {
                "item_id": "first",
                "title": "Initial item",
                "complexity_score": 0.4,
            }
        ],
    )

    await service.update_item_status(
        session_id="update-session",
        task_id="update-task",
        item_id="first",
        status="completed",
        notes="Done",
    )

    assert (
        fake_runtime_state.saved["update-session"]["todo_planning"]["tasks"]["update-task"]["todo_list"]["items"][0]["status"]
        == "completed"
    )


@pytest.mark.asyncio
async def test_todo_planning_service_retry_reopens_failed_items() -> None:
    from mindflow_backend.services.orchestration.todo_planning_service import TodoPlanningService

    service = TodoPlanningService()
    await service.replace_list(
        session_id="retry-session",
        task_id="retry-task",
        goal="Retry failed work",
        source="planner",
        items=[
            {
                "item_id": "done",
                "title": "Completed item",
                "status": "completed",
                "complexity_score": 0.2,
            },
            {
                "item_id": "failed",
                "title": "Failed item",
                "status": "failed",
                "complexity_score": 0.8,
            },
            {
                "item_id": "downstream",
                "title": "Downstream item",
                "status": "completed",
                "dependencies": ["failed"],
                "complexity_score": 0.5,
            },
        ],
    )

    retried = await service.retry_items(
        session_id="retry-session",
        task_id="retry-task",
        retry_subtasks=True,
        retry_from_beginning=False,
    )
    statuses = {item.item_id: item.status for item in retried.todo_list.items}

    assert statuses["done"] == "completed"
    assert statuses["failed"] == "pending"
    assert statuses["downstream"] == "pending"
