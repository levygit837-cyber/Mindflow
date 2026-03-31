"""In-memory planning service for session-scoped orchestrator todo lists."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.planning import (
    TodoItemContract,
    TodoItemStatus,
    TodoListContract,
    TodoListFocusResponse,
    TodoListReadResponse,
    TodoListSummary,
)

if TYPE_CHECKING:
    from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
        SubTaskContract,
    )

_logger = get_logger(__name__)

_OPEN_STATUSES = {
    TodoItemStatus.PENDING,
    TodoItemStatus.IN_PROGRESS,
    TodoItemStatus.BLOCKED,
    TodoItemStatus.FAILED,
}
_PRIORITY_WEIGHT = {"low": 1, "medium": 2, "high": 3}
_OWNER_WEIGHT = {
    "coder": 0.12,
    "analyst": 0.08,
    "researcher": 0.06,
    "arch_tech": 0.14,
    "critic": 0.1,
}


def _get_session_runtime_state_service():
    try:
        from mindflow_backend.services.core import get_session_runtime_state_service
        return get_session_runtime_state_service()
    except Exception as exc:
        _logger.warning("todo_session_runtime_state_service_unavailable", error=str(exc))
        return None

def normalize_complexity_score(
    raw_score: float | None = None,
    *,
    priority: str = "medium",
    owner_agent: str | None = None,
    dependencies_count: int = 0,
    description: str = "",
    artifacts_count: int = 0,
    overall_complexity: float | None = None,
) -> float:
    """Normalize task complexity into the [0, 1] interval using runtime heuristics."""
    if raw_score is not None:
        return min(max(raw_score, 0.0), 1.0)
        
    base = 0.35
    if overall_complexity is not None:
        base = max(base, min(max(overall_complexity, 0.0), 1.0) * 0.45)

    base += 0.08 * min(dependencies_count, 3)
    base += 0.04 * min(artifacts_count, 3)
    base += _OWNER_WEIGHT.get((owner_agent or "").lower(), 0.0)
    base += {1: 0.0, 2: 0.07, 3: 0.14}.get(_PRIORITY_WEIGHT.get(priority, 2), 0.07)

    # Note: Description word count removed as it was arbitrary and brittle.
    # We now strictly rely on structural heuristics (dependencies, artifacts, priority, owner).

    return round(min(max(base, 0.0), 1.0), 3)


def _complexity_reason(
    *,
    owner_agent: str | None,
    priority: str,
    dependencies_count: int,
    description: str,
) -> str:
    parts: list[str] = []
    if dependencies_count:
        parts.append(f"{dependencies_count} dependenc{'y' if dependencies_count == 1 else 'ies'}")
    if owner_agent:
        parts.append(f"owned by {owner_agent}")
    if priority:
        parts.append(f"{priority} priority")
    if len(description.split()) > 16:
        parts.append("broader task scope")
    return ", ".join(parts) or "baseline runtime complexity"


def build_todo_items_from_plan(
    plan: list[dict[str, Any]],
    *,
    overall_complexity: float | None = None,
) -> list[TodoItemContract]:
    """Project a planner JSON array into normalized todo items."""
    items: list[TodoItemContract] = []
    for index, raw in enumerate(plan):
        description = str(raw.get("description") or raw.get("task") or "")
        dependencies = [str(dep) for dep in raw.get("dependencies", []) if dep is not None]
        priority = str(raw.get("priority") or "medium")
        owner_agent = str(raw.get("agent") or raw.get("owner_agent") or "analyst")
        score = normalize_complexity_score(
            raw.get("complexity_score"),
            priority=priority,
            owner_agent=owner_agent,
            dependencies_count=len(dependencies),
            description=description,
            artifacts_count=len(raw.get("estimated_tools", []) or []),
            overall_complexity=overall_complexity,
        )
        items.append(
            TodoItemContract(
                item_id=str(raw.get("item_id") or raw.get("task_id") or f"plan-step-{index + 1}"),
                title=str(raw.get("task") or raw.get("title") or f"Step {index + 1}"),
                description=description,
                owner_agent=owner_agent,
                priority=priority,
                dependencies=dependencies,
                complexity_score=score,
                complexity_reason=str(raw.get("complexity_reason") or _complexity_reason(
                    owner_agent=owner_agent,
                    priority=priority,
                    dependencies_count=len(dependencies),
                    description=description,
                )),
            )
        )
    return items


def build_todo_items_from_subtasks(
    components: list[SubTaskContract],
    *,
    overall_complexity: float | None = None,
) -> list[TodoItemContract]:
    """Project decomposition subtasks into normalized todo items."""
    items: list[TodoItemContract] = []
    for component in components:
        owner_agent = component.owner_agent.value
        priority = component.priority
        description = component.scope
        dependencies = [str(dep) for dep in component.dependencies]
        score = normalize_complexity_score(
            getattr(component, "complexity_score", None),
            priority=priority,
            owner_agent=owner_agent,
            dependencies_count=len(dependencies),
            description=description,
            artifacts_count=len(component.expected_artifacts),
            overall_complexity=overall_complexity,
        )
        items.append(
            TodoItemContract(
                item_id=str(component.task_id),
                title=component.title,
                description=description,
                owner_agent=owner_agent,
                priority=priority,
                dependencies=dependencies,
                complexity_score=score,
                complexity_reason=getattr(component, "complexity_reason", "") or _complexity_reason(
                    owner_agent=owner_agent,
                    priority=priority,
                    dependencies_count=len(dependencies),
                    description=description,
                ),
            )
        )
    return items


class TodoPlanningService:
    """Manage session + task scoped todo lists used by orchestrator planning flows."""

    def __init__(self, *, stale_after: timedelta = timedelta(minutes=15)) -> None:
        self._lists: dict[str, dict[str, TodoListContract]] = defaultdict(dict)
        self._task_index: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._stale_after = stale_after

    async def replace_list(
        self,
        session_id: str,
        task_id: str,
        goal: str,
        items: list[dict[str, Any] | TodoItemContract],
        source: str,
    ) -> TodoListReadResponse:
        await self._ensure_session_loaded(session_id)
        now = self._now()
        async with self._lock:
            existing = self._lists.get(session_id, {}).get(task_id)
            existing_items = {
                item.item_id: item
                for item in (existing.items if existing else [])
            }
            normalized_items = [
                self._coerce_item(raw_item, existing_items.get(self._extract_item_id(raw_item)), now)
                for raw_item in items
            ]
            todo_list = TodoListContract(
                session_id=session_id,
                task_id=task_id,
                goal=goal,
                source=source,
                items=normalized_items,
                created_at=existing.created_at if existing else now,
                updated_at=now,
                closed_at=None if normalized_items and any(item.status in _OPEN_STATUSES for item in normalized_items) else now,
            )
            self._lists[session_id][task_id] = todo_list
            self._task_index[task_id] = session_id

        _logger.info(
            "todo_list_replaced",
            session_id=session_id,
            task_id=task_id,
            items=len(normalized_items),
            source=source,
        )
        await self._persist_session_state(session_id)
        return await self.get_list(session_id, task_id)

    async def get_list(self, session_id: str, task_id: str) -> TodoListReadResponse:
        await self._ensure_session_loaded(session_id)
        todo_list = self._get_required_list(session_id, task_id)
        return TodoListReadResponse(
            todo_list=todo_list.model_copy(deep=True),
            summary=self._build_summary(todo_list),
        )

    async def get_session_lists(self, session_id: str) -> list[TodoListSummary]:
        await self._ensure_session_loaded(session_id)
        lists = list(self._lists.get(session_id, {}).values())
        lists.sort(key=lambda todo_list: todo_list.updated_at, reverse=True)
        return [self._build_summary(todo_list) for todo_list in lists]

    async def get_list_by_task_id(self, task_id: str) -> TodoListReadResponse:
        session_id = self._task_index.get(task_id)
        if session_id is None:
            raise ValueError(f"Todo list not found for task={task_id}")
        await self._ensure_session_loaded(session_id)
        return await self.get_list(session_id=session_id, task_id=task_id)

    async def update_item_status(
        self,
        session_id: str,
        task_id: str,
        item_id: str,
        status: str,
        notes: str | None = None,
    ) -> TodoListReadResponse:
        await self._ensure_session_loaded(session_id)
        async with self._lock:
            todo_list = self._get_required_list(session_id, task_id)
            item = next((candidate for candidate in todo_list.items if candidate.item_id == item_id), None)
            if item is None:
                raise ValueError(f"Todo item not found: {item_id}")

            normalized_status = TodoItemStatus(status)
            now = self._now()
            item.status = normalized_status
            item.notes = notes if notes is not None else item.notes
            item.updated_at = now
            item.completed_at = now if normalized_status == TodoItemStatus.COMPLETED else None
            todo_list.updated_at = now
            if all(candidate.status == TodoItemStatus.COMPLETED for candidate in todo_list.items):
                todo_list.closed_at = now
            else:
                todo_list.closed_at = None

        _logger.info(
            "todo_item_status_updated",
            session_id=session_id,
            task_id=task_id,
            item_id=item_id,
            status=status,
        )
        await self._persist_session_state(session_id)
        return await self.get_list(session_id, task_id)

    async def focus_complex_items(
        self,
        session_id: str,
        task_id: str,
        limit: int = 3,
    ) -> TodoListFocusResponse:
        await self._ensure_session_loaded(session_id)
        todo_list = self._get_required_list(session_id, task_id)
        open_items = [
            item.model_copy(deep=True)
            for item in todo_list.items
            if item.status in _OPEN_STATUSES
        ]
        open_items.sort(
            key=lambda item: (
                -item.complexity_score,
                -len(item.dependencies),
                -_PRIORITY_WEIGHT.get(item.priority, 2),
                item.title.lower(),
            )
        )
        summary = self._build_summary(todo_list)
        return TodoListFocusResponse(
            task_id=task_id,
            goal=todo_list.goal,
            items=open_items[: max(limit, 1)],
            summary=summary,
        )

    async def is_stale(self, session_id: str, task_id: str) -> bool:
        await self._ensure_session_loaded(session_id)
        todo_list = self._lists.get(session_id, {}).get(task_id)
        if todo_list is None:
            return True
        if todo_list.closed_at is not None:
            return False
        if not any(item.status in _OPEN_STATUSES for item in todo_list.items):
            return False
        return (self._now() - todo_list.updated_at) > self._stale_after

    async def close_list(self, session_id: str, task_id: str) -> TodoListReadResponse:
        await self._ensure_session_loaded(session_id)
        async with self._lock:
            todo_list = self._get_required_list(session_id, task_id)
            todo_list.closed_at = self._now()
            todo_list.updated_at = todo_list.closed_at
        await self._persist_session_state(session_id)
        return await self.get_list(session_id, task_id)

    def _extract_item_id(self, raw_item: dict[str, Any] | TodoItemContract) -> str:
        if isinstance(raw_item, TodoItemContract):
            return raw_item.item_id
        item_id = raw_item.get("item_id") or raw_item.get("task_id")
        if item_id is None:
            raise ValueError("Todo items require item_id or task_id")
        return str(item_id)

    def _coerce_item(
        self,
        raw_item: dict[str, Any] | TodoItemContract,
        previous: TodoItemContract | None,
        now: datetime,
    ) -> TodoItemContract:
        if isinstance(raw_item, TodoItemContract):
            item = raw_item.model_copy(deep=True)
        else:
            item = TodoItemContract.model_validate(raw_item)

        item.dependencies = [str(dep) for dep in item.dependencies]
        item.complexity_score = normalize_complexity_score(
            item.complexity_score,
            priority=item.priority,
            owner_agent=item.owner_agent,
            dependencies_count=len(item.dependencies),
            description=item.description or item.title,
        )
        if not item.complexity_reason:
            item.complexity_reason = _complexity_reason(
                owner_agent=item.owner_agent,
                priority=item.priority,
                dependencies_count=len(item.dependencies),
                description=item.description or item.title,
            )

        if previous is not None:
            item.created_at = previous.created_at
            if item.status == TodoItemStatus.PENDING and previous.status != TodoItemStatus.PENDING:
                item.status = previous.status
                item.notes = previous.notes
                item.completed_at = previous.completed_at

        item.updated_at = now
        return item

    def _get_required_list(self, session_id: str, task_id: str) -> TodoListContract:
        todo_list = self._lists.get(session_id, {}).get(task_id)
        if todo_list is None:
            raise ValueError(f"Todo list not found for session={session_id} task={task_id}")
        return todo_list

    async def _ensure_session_loaded(self, session_id: str) -> None:
        if self._lists.get(session_id):
            return

        service = _get_session_runtime_state_service()
        if service is None:
            return
        if service is None:
            return

        try:
            snapshot = await service.load_session_state(session_id)
        except Exception as exc:
            _logger.warning("todo_session_state_load_failed", session_id=session_id, error=str(exc))
            return

        if not snapshot:
            return

        todo_state = snapshot.get("todo_planning")
        if not isinstance(todo_state, dict):
            return

        tasks = todo_state.get("tasks")
        if not isinstance(tasks, dict):
            return

        session_lists = self._lists[session_id]
        for task_id, task_state in tasks.items():
            todo_payload: Any
            if isinstance(task_state, dict) and "todo_list" in task_state:
                todo_payload = task_state["todo_list"]
            else:
                todo_payload = task_state

            try:
                todo_list = TodoListContract.model_validate(todo_payload)
            except Exception as exc:
                _logger.warning(
                    "todo_session_state_restore_failed",
                    session_id=session_id,
                    task_id=task_id,
                    error=str(exc),
                )
                continue

            session_lists[task_id] = todo_list
            self._task_index[task_id] = session_id

    async def _persist_session_state(self, session_id: str) -> None:
        service = _get_session_runtime_state_service()
        if service is None:
            return
        if service is None:
            return

        session_lists = self._lists.get(session_id, {})
        payload = {
            "todo_planning": {
                "tasks": {
                    task_id: {
                        "todo_list": todo_list.model_dump(mode="json"),
                        "summary": self._build_summary(todo_list).model_dump(mode="json"),
                    }
                    for task_id, todo_list in session_lists.items()
                }
            }
        }

        try:
            await service.save_session_state(session_id, payload)
        except Exception as exc:
            _logger.warning("todo_session_state_persist_failed", session_id=session_id, error=str(exc))

    def _build_summary(self, todo_list: TodoListContract) -> TodoListSummary:
        completed_items = sum(1 for item in todo_list.items if item.status == TodoItemStatus.COMPLETED)
        blocked_items = sum(1 for item in todo_list.items if item.status == TodoItemStatus.BLOCKED)
        failed_items = sum(1 for item in todo_list.items if item.status == TodoItemStatus.FAILED)
        open_items = sum(1 for item in todo_list.items if item.status in _OPEN_STATUSES)

        total_complexity = sum(max(item.complexity_score, 0.1) for item in todo_list.items)
        completed_complexity = sum(
            max(item.complexity_score, 0.1)
            for item in todo_list.items
            if item.status == TodoItemStatus.COMPLETED
        )
        pending_complexity = sum(
            item.complexity_score
            for item in todo_list.items
            if item.status in _OPEN_STATUSES
        )
        highest_open_complexity = max(
            (item.complexity_score for item in todo_list.items if item.status in _OPEN_STATUSES),
            default=0.0,
        )

        progress = 100.0 if total_complexity == 0 else round((completed_complexity / total_complexity) * 100.0, 2)
        return TodoListSummary(
            session_id=todo_list.session_id,
            task_id=todo_list.task_id,
            goal=todo_list.goal,
            source=todo_list.source,
            total_items=len(todo_list.items),
            completed_items=completed_items,
            open_items=open_items,
            blocked_items=blocked_items,
            failed_items=failed_items,
            progress_percentage=progress,
            pending_complexity=round(pending_complexity, 3),
            highest_open_complexity=round(highest_open_complexity, 3),
            is_stale=(self._now() - todo_list.updated_at) > self._stale_after if todo_list.closed_at is None else False,
            updated_at=todo_list.updated_at,
            closed_at=todo_list.closed_at,
        )

    def _now(self) -> datetime:
        return datetime.now(UTC)
