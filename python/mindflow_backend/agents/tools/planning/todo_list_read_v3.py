"""TodoListReadTool v3 - New Tool System Implementation.

Read the current todo list snapshot for a planned execution task.
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


class TodoListReadInput(BaseModel):
    """Input schema for TodoListReadTool v3."""

    task_id: str = Field(
        description="Planned execution task identifier"
    )
    session_id: str | None = Field(
        default=None,
        description="Chat session identifier (optional, can be inferred from context)"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def todo_list_read_execute(input: TodoListReadInput, context: ToolContext) -> dict[str, Any]:
    """Read the current todo list for a planning task.

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

        # Get todo list
        snapshot = await service.get_list(
            session_id=str(session_id),
            task_id=input.task_id,
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
            "error": f"Failed to read todo list: {e}",
            "error_code": "READ_ERROR",
            "task_id": input.task_id
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


TodoListReadToolV3 = build_tool(
    name="read_todos",
    description=(
        "Read the latest todo list snapshot for a planned execution task. "
        "Returns the complete list with all items, their status, complexity, and metadata. "
        "Used to check current progress and plan next steps."
    ),
    input_schema=TodoListReadInput,
    execute=todo_list_read_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
