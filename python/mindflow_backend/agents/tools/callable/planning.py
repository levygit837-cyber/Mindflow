"""Planning tools - Callable pattern (Phase 2).

All tools in this module use:
- Pydantic input schemas for type safety
- CallableToolResult return type
- ToolContext for runtime state (root_dir, sandbox_mode, permissions)
- Appropriate factories (build_readonly_tool, build_callable_tool)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.callable import CallableToolResult, ProgressCallback
from mindflow_backend.schemas.tools.callable_builder import (
    build_readonly_tool,
    build_callable_tool,
)
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.services import get_todo_planning_service


# ---------------------------------------------------------------------------
# TodoListReadCallable - Priority 5
# ---------------------------------------------------------------------------


class TodoListReadInput(BaseModel):
    """Input schema for TodoListReadCallable."""

    task_id: str = Field(
        description="Planned execution task identifier"
    )
    session_id: str | None = Field(
        default=None,
        description="Chat session identifier (optional, can be inferred from context)"
    )


async def todo_list_read_impl(
    input: TodoListReadInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Read the current todo list for a planning task.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with todo list snapshot or error
    """
    try:
        # Resolve session_id
        session_id = input.session_id
        if not session_id:
            # Try to get from context metadata
            session_id = context.session_id or context.metadata.get("session_id")

        if not session_id:
            return CallableToolResult(
                data=None,
                success=False,
                error="session_id is required for planning operations",
                metadata={
                    "error_code": "MISSING_SESSION_ID",
                    "task_id": input.task_id,
                }
            )

        # Get planning service
        service = get_todo_planning_service()

        # Get todo list
        snapshot = await service.get_list(
            session_id=str(session_id),
            task_id=input.task_id,
        )

        return CallableToolResult(
            data={
                "task_id": input.task_id,
                "session_id": str(session_id),
                "snapshot": snapshot.model_dump(mode="json"),
            },
            success=True,
            metadata={
                "operation": "read_todos",
            }
        )

    except ValueError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Validation error: {e}",
            metadata={
                "error_code": "VALIDATION_ERROR",
                "task_id": input.task_id,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Failed to read todo list: {e}",
            metadata={
                "error_code": "READ_ERROR",
                "task_id": input.task_id,
            }
        )


TodoListReadCallable = build_readonly_tool(
    name="read_todos",
    description=(
        "Read the latest todo list snapshot for a planned execution task. "
        "Returns the complete list with all items, their status, complexity, and metadata. "
        "Used to check current progress and plan next steps. "
        "Concurrent-safe: can read multiple todo lists in parallel."
    ),
    input_schema=TodoListReadInput,
    call_fn=todo_list_read_impl,
    is_concurrency_safe=True,  # Safe to read multiple todo lists in parallel
    interrupt_behavior="cancel",  # Safe to interrupt todo list reads
)


# ---------------------------------------------------------------------------
# TodoListWriteCallable - Priority 5
# ---------------------------------------------------------------------------


class TodoListWriteInput(BaseModel):
    """Input schema for TodoListWriteCallable."""

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


async def todo_list_write_impl(
    input: TodoListWriteInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Replace the todo list for a planning task.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with todo list snapshot or error
    """
    try:
        # Resolve session_id
        session_id = input.session_id
        if not session_id:
            # Try to get from context metadata
            session_id = context.session_id or context.metadata.get("session_id")

        if not session_id:
            return CallableToolResult(
                data=None,
                success=False,
                error="session_id is required for planning operations",
                metadata={
                    "error_code": "MISSING_SESSION_ID",
                    "task_id": input.task_id,
                }
            )

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

        return CallableToolResult(
            data={
                "task_id": input.task_id,
                "session_id": str(session_id),
                "snapshot": snapshot.model_dump(mode="json"),
            },
            success=True,
            metadata={
                "operation": "write_todos",
            }
        )

    except ValueError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Validation error: {e}",
            metadata={
                "error_code": "VALIDATION_ERROR",
                "task_id": input.task_id,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Failed to write todo list: {e}",
            metadata={
                "error_code": "WRITE_ERROR",
                "task_id": input.task_id,
            }
        )


TodoListWriteCallable = build_callable_tool(
    name="write_todos",
    description=(
        "Replace the session-scoped todo list for a planned execution task. "
        "Persists the complete list of todo items with their status, complexity, and metadata. "
        "Used by planners and runtime to track task progress. "
        "NOT concurrent-safe: modifies session state."
    ),
    input_schema=TodoListWriteInput,
    call_fn=todo_list_write_impl,
    is_read_only=False,  # Modifies session state
    is_concurrency_safe=False,  # Modifies session state
    is_destructive=False,  # Replaces but doesn't delete
    interrupt_behavior="block",  # Don't interrupt todo list writes
)


# ---------------------------------------------------------------------------
# TodoListFocusCallable - Priority 5
# ---------------------------------------------------------------------------


class TodoListFocusInput(BaseModel):
    """Input schema for TodoListFocusCallable."""

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


async def todo_list_focus_impl(
    input: TodoListFocusInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Return the most complex open items from a planning todo list.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with focused todo items or error
    """
    try:
        # Resolve session_id
        session_id = input.session_id
        if not session_id:
            # Try to get from context metadata
            session_id = context.session_id or context.metadata.get("session_id")

        if not session_id:
            return CallableToolResult(
                data=None,
                success=False,
                error="session_id is required for planning operations",
                metadata={
                    "error_code": "MISSING_SESSION_ID",
                    "task_id": input.task_id,
                }
            )

        # Get planning service
        service = get_todo_planning_service()

        # Get focused items
        focused = await service.focus_complex_items(
            session_id=str(session_id),
            task_id=input.task_id,
            limit=input.limit,
        )

        return CallableToolResult(
            data={
                "task_id": input.task_id,
                "session_id": str(session_id),
                "limit": input.limit,
                "focused_items": focused.model_dump(mode="json"),
            },
            success=True,
            metadata={
                "operation": "focus_todos",
            }
        )

    except ValueError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Validation error: {e}",
            metadata={
                "error_code": "VALIDATION_ERROR",
                "task_id": input.task_id,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Failed to focus todo items: {e}",
            metadata={
                "error_code": "FOCUS_ERROR",
                "task_id": input.task_id,
            }
        )


TodoListFocusCallable = build_readonly_tool(
    name="focus_todos",
    description=(
        "Return the most complex open todo items for the current planned execution task. "
        "Prioritizes items by complexity to help focus on the most challenging work first. "
        "Useful for breaking down complex tasks and planning execution order. "
        "Concurrent-safe: can read multiple todo lists in parallel."
    ),
    input_schema=TodoListFocusInput,
    call_fn=todo_list_focus_impl,
    is_concurrency_safe=True,  # Safe to read multiple todo lists in parallel
    interrupt_behavior="cancel",  # Safe to interrupt todo list reads
)
