"""TodoListWriteTool v3 - New Tool System Implementation.

Replace the todo list for a planned execution task with session-scoped persistence.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.planning import todo_list as canonical_planning
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
        session_id, snapshot = await canonical_planning.write_todo_snapshot(
            task_id=input.task_id,
            goal=str(input.goal),
            items=input.items,
            source=input.source,
            session_id=input.session_id,
            context_session_id=context.session_id,
            context_metadata=context.metadata,
            service=get_todo_planning_service(),
        )

        return {
            "success": True,
            "task_id": input.task_id,
            "session_id": session_id,
            "snapshot": snapshot,
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "MISSING_SESSION_ID",
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
