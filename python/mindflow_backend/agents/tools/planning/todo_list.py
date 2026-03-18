"""Session-scoped planning tools for orchestrator todo lists."""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.schemas.tools.planning import (
    FOCUS_TODOS_SCHEMA,
    READ_TODOS_SCHEMA,
    WRITE_TODOS_SCHEMA,
)
from mindflow_backend.services import get_todo_planning_service


class _PlanningToolBase(AsyncToolInterface):
    def __init__(self) -> None:
        super().__init__()
        self._service = get_todo_planning_service()

    def _resolve_session_id(self, kwargs: dict[str, Any]) -> str:
        session_id = kwargs.get("session_id") or self.session_id
        if not session_id:
            raise ValueError("session_id is required for planning operations")
        return str(session_id)


class WriteTodosTool(_PlanningToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "write_todos"
        self.description = "Replace the todo list for a planning task"
        self._schema = WRITE_TODOS_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        snapshot = await self._service.replace_list(
            session_id=session_id,
            task_id=str(kwargs["task_id"]),
            goal=str(kwargs["goal"]),
            items=list(kwargs.get("items") or []),
            source=str(kwargs.get("source") or "planner"),
        )
        return self._format_result(success=True, result=snapshot.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class ReadTodosTool(_PlanningToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "read_todos"
        self.description = "Read the current todo list for a planning task"
        self._schema = READ_TODOS_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        snapshot = await self._service.get_list(
            session_id=session_id,
            task_id=str(kwargs["task_id"]),
        )
        return self._format_result(success=True, result=snapshot.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class FocusTodosTool(_PlanningToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "focus_todos"
        self.description = "Return the most complex open items from a planning todo list"
        self._schema = FOCUS_TODOS_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        focused = await self._service.focus_complex_items(
            session_id=session_id,
            task_id=str(kwargs["task_id"]),
            limit=int(kwargs.get("limit") or 3),
        )
        return self._format_result(success=True, result=focused.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()
