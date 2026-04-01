"""TodoListWriteTool v3 - New Tool System Implementation.

Replace the todo list for a planned execution task with session-scoped persistence.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.services import get_todo_planning_service


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class TodoListWriteInput(BaseModel):
    """Input schema for TodoListWriteTool v3."""

    task_id: str = Field(
        description="Planned execution task identifier"
    )
    goal: str = Field(
        description="High-level goal for the todo list"
    )
    items: list[dict[str, Any]] = Field(
        default=[],
        description="Full todo item list to persist (each item should have: description, status, complexity, etc.)"
    )
    source: str = Field(
        default="planner",
        description="Planner/runtime source for the list"
    )
    session_id: str | None = Field(
        default=None,
        description="Chat session identifier (optional, can be inferred from context)"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def todo_list_write_execute(input: TodoListWriteInput, context: ToolContext) -> dict[str, Any]:
    """Replace the todo list for a planning task.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with todo list snapshot or error
    """
    try:
        # Resolve session_id
        session_id = input.session_id
        if not session_id:
            # Try to get from context metadata
            session_id = context.metadata.get("session_id")

        if not session_id:
            return {
                "success": False,
                "error": "session_id is required for planning operations",
                "error_code": "MISSING_SESSION_ID",
                "task_id": input.task_id
            }

        # Get planning service
        service = get_todo_planning_service()

        # Replace todo list
        snapshot = await service.replace_list(
            session_id=str(session_id),
            task_id=input.task_id,
            goal=input.goal,
            items=input.items,
            source=input.source,
        )

        return {
            "success": True,
            "task_id": input.task_id,
            "session_id": str(session_id),
            "snapshot": snapshot.model_dump(mode="json")
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Validation error: {e}",
            "error_code": "VALIDATION_ERROR",
            "task_id": input.task_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to write todo list: {e}",
            "error_code": "WRITE_ERROR",
            "task_id": input.task_id
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


TodoListWriteToolV3 = build_tool(
    name="write_todos",
    description=(
        "Replace the session-scoped todo list for a planned execution task. "
        "Persists the complete list of todo items with their status, complexity, and metadata. "
        "Used by planners and runtime to track task progress."
    ),
    input_schema=TodoListWriteInput,
    execute=todo_list_write_execute,
    is_read_only=False,
    is_concurrency_safe=False,  # Modifies session state
    is_destructive=False,  # Replaces but doesn't delete
)
