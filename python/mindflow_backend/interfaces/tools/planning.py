"""Planning tool interfaces for todo-list management."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PlanningToolInterface(Protocol):
    """Marker protocol for planning-oriented tools."""

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the planning tool."""
        ...

    def get_schema(self) -> dict[str, Any]:
        """Return the planning tool schema."""
        ...


@runtime_checkable
class TodoListWriteTool(PlanningToolInterface, Protocol):
    """Replace the persisted todo list for a task."""


@runtime_checkable
class TodoListReadTool(PlanningToolInterface, Protocol):
    """Read the persisted todo list for a task."""


@runtime_checkable
class TodoListFocusTool(PlanningToolInterface, Protocol):
    """Return the most relevant open todo items for a task."""
