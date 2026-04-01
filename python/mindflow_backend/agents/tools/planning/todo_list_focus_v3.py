"""TodoListFocusTool v3 - New Tool System Implementation.

Return the most complex open todo items for focused execution.
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


class TodoListFocusInput(BaseModel):
    """Input schema for TodoListFocusTool v3."""

    task_id: str = Field(
        description="Planned execution task identifier"
    )
    limit: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of items to return"
    )
    session_id: str | None = Field(
        default=None,
        description="Chat session identifier (optional, can be inferred from context)"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def todo_list_focus_execute(input: TodoListFocusInput, context: ToolContext) -> dict[str, Any]:
    """Return the most complex open items from a planning todo list.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with focused todo items or error
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

        # Get focused items
        focused = await service.focus_complex_items(
            session_id=str(session_id),
            task_id=input.task_id,
            limit=input.limit,
        )

        return {
            "success": True,
            "task_id": input.task_id,
            "session_id": str(session_id),
            "limit": input.limit,
            "focused_items": focused.model_dump(mode="json")
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
            "error": f"Failed to focus todo items: {e}",
            "error_code": "FOCUS_ERROR",
            "task_id": input.task_id
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


TodoListFocusToolV3 = build_tool(
    name="focus_todos",
    description=(
        "Return the most complex open todo items for the current planned execution task. "
        "Prioritizes items by complexity to help focus on the most challenging work first. "
        "Useful for breaking down complex tasks and planning execution order."
    ),
    input_schema=TodoListFocusInput,
    execute=todo_list_focus_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
