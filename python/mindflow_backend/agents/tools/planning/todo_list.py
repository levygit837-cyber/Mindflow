"""Session-scoped planning tools for orchestrator todo lists."""

from __future__ import annotations

from typing import Any, Mapping

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.schemas.tools.planning import (
    FOCUS_TODOS_SCHEMA,
    READ_TODOS_SCHEMA,
    WRITE_TODOS_SCHEMA,
)
from mindflow_backend.services import get_todo_planning_service


def resolve_planning_session_id(
    *,
    session_id: Any | None = None,
    tool_session_id: Any | None = None,
    context_session_id: Any | None = None,
    context_metadata: Mapping[str, Any] | None = None,
) -> str:
    """Resolve planning session state from all supported runtime surfaces."""
    resolved = session_id or tool_session_id or context_session_id
    if not resolved and context_metadata:
        resolved = context_metadata.get("session_id")
    if not resolved:
        raise ValueError("session_id is required for planning operations")
    return str(resolved)


async def read_todo_snapshot(
    *,
    task_id: str,
    session_id: Any | None = None,
    tool_session_id: Any | None = None,
    context_session_id: Any | None = None,
    context_metadata: Mapping[str, Any] | None = None,
    service: Any | None = None,
) -> tuple[str, dict[str, Any]]:
    """Read the latest todo snapshot using the canonical planning service path."""
    resolved_session_id = resolve_planning_session_id(
        session_id=session_id,
        tool_session_id=tool_session_id,
        context_session_id=context_session_id,
        context_metadata=context_metadata,
    )
    planning_service = service or get_todo_planning_service()
    snapshot = await planning_service.get_list(
        session_id=resolved_session_id,
        task_id=str(task_id),
    )
    return resolved_session_id, snapshot.model_dump(mode="json")


async def write_todo_snapshot(
    *,
    task_id: str,
    goal: str,
    items: list[dict[str, Any]] | None = None,
    source: str = "planner",
    session_id: Any | None = None,
    tool_session_id: Any | None = None,
    context_session_id: Any | None = None,
    context_metadata: Mapping[str, Any] | None = None,
    service: Any | None = None,
) -> tuple[str, dict[str, Any]]:
    """Replace the todo snapshot using the canonical planning service path."""
    resolved_session_id = resolve_planning_session_id(
        session_id=session_id,
        tool_session_id=tool_session_id,
        context_session_id=context_session_id,
        context_metadata=context_metadata,
    )
    planning_service = service or get_todo_planning_service()
    snapshot = await planning_service.replace_list(
        session_id=resolved_session_id,
        task_id=str(task_id),
        goal=str(goal),
        items=list(items or []),
        source=str(source or "planner"),
    )
    return resolved_session_id, snapshot.model_dump(mode="json")


async def focus_todo_items(
    *,
    task_id: str,
    limit: int = 3,
    session_id: Any | None = None,
    tool_session_id: Any | None = None,
    context_session_id: Any | None = None,
    context_metadata: Mapping[str, Any] | None = None,
    service: Any | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return focused todo items using the canonical planning service path."""
    resolved_session_id = resolve_planning_session_id(
        session_id=session_id,
        tool_session_id=tool_session_id,
        context_session_id=context_session_id,
        context_metadata=context_metadata,
    )
    planning_service = service or get_todo_planning_service()
    focused = await planning_service.focus_complex_items(
        session_id=resolved_session_id,
        task_id=str(task_id),
        limit=int(limit),
    )
    return resolved_session_id, focused.model_dump(mode="json")


class _PlanningToolBase(AsyncToolInterface):
    def __init__(self) -> None:
        super().__init__()
        self._service = get_todo_planning_service()


class WriteTodosTool(_PlanningToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "write_todos"
        self.description = "Replace the todo list for a planning task"
        self._schema = WRITE_TODOS_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        _, snapshot = await write_todo_snapshot(
            task_id=str(kwargs["task_id"]),
            goal=str(kwargs["goal"]),
            items=list(kwargs.get("items") or []),
            source=str(kwargs.get("source") or "planner"),
            session_id=kwargs.get("session_id"),
            tool_session_id=self.session_id,
            service=self._service,
        )
        return self._format_result(success=True, result=snapshot)

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class ReadTodosTool(_PlanningToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "read_todos"
        self.description = "Read the current todo list for a planning task"
        self._schema = READ_TODOS_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        _, snapshot = await read_todo_snapshot(
            task_id=str(kwargs["task_id"]),
            session_id=kwargs.get("session_id"),
            tool_session_id=self.session_id,
            service=self._service,
        )
        return self._format_result(success=True, result=snapshot)

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class FocusTodosTool(_PlanningToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "focus_todos"
        self.description = "Return the most complex open items from a planning todo list"
        self._schema = FOCUS_TODOS_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        _, focused = await focus_todo_items(
            task_id=str(kwargs["task_id"]),
            limit=int(kwargs.get("limit") or 3),
            session_id=kwargs.get("session_id"),
            tool_session_id=self.session_id,
            service=self._service,
        )
        return self._format_result(success=True, result=focused)

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()
