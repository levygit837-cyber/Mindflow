"""Factory for creating callable tools with safe defaults.

This module provides the `build_callable_tool()` factory function that
mirrors Claude Code's `buildTool()` pattern. It creates CallableTool
instances with fail-closed defaults for all permission flags.

Key principles:
- All permission flags default to False (fail-closed)
- Tools must explicitly opt-in to read-only, concurrent, or destructive behavior
- Factory handles boilerplate so tool implementations stay focused

Example:
    async def read_file_impl(input: FileReadInput, ctx: ToolContext) -> ToolResult[str]:
        content = await read_file(input.file_path)
        return ToolResult(data=content)

    FileReadTool = build_callable_tool(
        name="file_read",
        description="Read file contents from filesystem",
        input_schema=FileReadInput,
        call_fn=read_file_impl,
        is_read_only=True,
        is_concurrency_safe=True,
        interrupt_behavior="cancel",
    )
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TypeVar

from pydantic import BaseModel

from mindflow_backend.schemas.tools.callable import CallableTool, ProgressCallback, ToolResult
from mindflow_backend.schemas.tools.context import ToolContext

# Type variables matching callable.py
I = TypeVar("I", bound=BaseModel)
O = TypeVar("O")

# Type alias for the call function signature
CallFunction = Callable[[I, ToolContext, ProgressCallback | None], Awaitable[ToolResult[O]]]


# ── Safe Defaults (fail-closed) ──

CALLABLE_TOOL_DEFAULTS = {
    "is_read_only": False,  # Assume tool writes
    "is_concurrency_safe": False,  # Assume not safe for parallel execution
    "is_destructive": False,  # Assume reversible operations
    "is_enabled": True,  # Assume tool is available
    "interrupt_behavior": "block",  # Assume should not be interrupted
}


# ── Factory Function ──


def build_callable_tool(
    name: str,
    description: str,
    input_schema: type[I],
    call_fn: CallFunction[I, O],
    *,
    is_read_only: bool | None = None,
    is_concurrency_safe: bool | None = None,
    is_destructive: bool | None = None,
    is_enabled: bool | None = None,
    interrupt_behavior: str | None = None,
    validate_input_fn: Callable[[I, ToolContext], Awaitable[tuple[bool, str | None]]] | None = None,
    check_permissions_fn: Callable[[I, ToolContext], Awaitable[dict[str, Any]]] | None = None,
) -> CallableTool[I, O]:
    """Create a callable tool with safe defaults.

    This factory mirrors Claude Code's buildTool() pattern, providing
    fail-closed defaults for all permission flags. Tools must explicitly
    opt-in to read-only, concurrent, or destructive behavior.

    Args:
        name: Tool name (unique identifier for tool calls)
        description: Tool description (shown to model and user)
        input_schema: Pydantic model defining valid input
        call_fn: Async function that implements the tool logic
            Signature: async (input: I, context: ToolContext, on_progress: Callback | None) -> ToolResult[O]

        is_read_only: True if tool never modifies state (default: False)
        is_concurrency_safe: True if tool can run in parallel (default: False)
        is_destructive: True if tool performs irreversible ops (default: False)
        is_enabled: True if tool is available (default: True)
        interrupt_behavior: 'cancel' or 'block' (default: 'block')

        validate_input_fn: Optional custom input validation function
        check_permissions_fn: Optional custom permission checking function

    Returns:
        Concrete CallableTool instance with all defaults applied

    Example:
        async def read_file_impl(input: FileReadInput, ctx: ToolContext, on_progress) -> ToolResult[str]:
            try:
                async with aiofiles.open(input.file_path, "r") as f:
                    content = await f.read()
                return ToolResult(data=content, success=True)
            except FileNotFoundError as e:
                return ToolResult(data=None, success=False, error=str(e))

        FileReadTool = build_callable_tool(
            name="file_read",
            description="Read file contents from filesystem",
            input_schema=FileReadInput,
            call_fn=read_file_impl,
            is_read_only=True,
            is_concurrency_safe=True,
            interrupt_behavior="cancel",
        )
    """

    # Apply defaults for None values (fail-closed)
    final_is_read_only = (
        is_read_only if is_read_only is not None else CALLABLE_TOOL_DEFAULTS["is_read_only"]
    )
    final_is_concurrency_safe = (
        is_concurrency_safe
        if is_concurrency_safe is not None
        else CALLABLE_TOOL_DEFAULTS["is_concurrency_safe"]
    )
    final_is_destructive = (
        is_destructive
        if is_destructive is not None
        else CALLABLE_TOOL_DEFAULTS["is_destructive"]
    )
    final_is_enabled = (
        is_enabled if is_enabled is not None else CALLABLE_TOOL_DEFAULTS["is_enabled"]
    )
    final_interrupt_behavior = (
        interrupt_behavior
        if interrupt_behavior is not None
        else CALLABLE_TOOL_DEFAULTS["interrupt_behavior"]
    )

    # Validate interrupt_behavior
    if final_interrupt_behavior not in ("cancel", "block"):
        raise ValueError(
            f"interrupt_behavior must be 'cancel' or 'block', got: {final_interrupt_behavior}"
        )

    # Create concrete implementation
    class _ConcreteCallableTool(CallableTool[I, O]):
        """Concrete tool implementation created by build_callable_tool()."""

        @property
        def name(self) -> str:
            return name

        @property
        def description(self) -> str:
            return description

        @property
        def input_schema(self) -> type[I]:
            return input_schema

        async def call(
            self,
            input: I,
            context: ToolContext,
            on_progress: ProgressCallback | None = None,
        ) -> ToolResult[O]:
            """Execute the tool using the provided call function."""
            return await call_fn(input, context, on_progress)

        def is_read_only(self, input: I) -> bool:
            return final_is_read_only

        def is_concurrency_safe(self, input: I) -> bool:
            return final_is_concurrency_safe

        def is_destructive(self, input: I) -> bool:
            return final_is_destructive

        def is_enabled(self) -> bool:
            return final_is_enabled

        def interrupt_behavior(self) -> str:
            return final_interrupt_behavior

        async def validate_input(
            self,
            input: I,
            context: ToolContext,
        ) -> tuple[bool, str | None]:
            """Use custom validation if provided, otherwise default."""
            if validate_input_fn is not None:
                return await validate_input_fn(input, context)
            return (True, None)

        async def check_permissions(
            self,
            input: I,
            context: ToolContext,
        ) -> dict[str, Any]:
            """Use custom permission check if provided, otherwise default."""
            if check_permissions_fn is not None:
                return await check_permissions_fn(input, context)
            return {"behavior": "allow", "updated_input": input}

    return _ConcreteCallableTool()


# ── Simplified Builder for Read-Only Tools ──


def build_readonly_tool(
    name: str,
    description: str,
    input_schema: type[I],
    call_fn: CallFunction[I, O],
    *,
    is_concurrency_safe: bool = True,
    interrupt_behavior: str = "cancel",
) -> CallableTool[I, O]:
    """Convenience builder for read-only tools.

    Read-only tools are common and have predictable defaults:
    - is_read_only=True
    - is_concurrency_safe=True (usually safe to run in parallel)
    - interrupt_behavior='cancel' (safe to interrupt)
    - is_destructive=False (read-only can't be destructive)

    Args:
        name: Tool name
        description: Tool description
        input_schema: Pydantic input model
        call_fn: Implementation function
        is_concurrency_safe: Override if tool has shared state (default: True)
        interrupt_behavior: Override if tool should block (default: 'cancel')

    Returns:
        CallableTool configured for read-only operations

    Example:
        FileReadTool = build_readonly_tool(
            name="file_read",
            description="Read file contents",
            input_schema=FileReadInput,
            call_fn=read_file_impl,
        )
    """
    return build_callable_tool(
        name=name,
        description=description,
        input_schema=input_schema,
        call_fn=call_fn,
        is_read_only=True,
        is_concurrency_safe=is_concurrency_safe,
        is_destructive=False,
        interrupt_behavior=interrupt_behavior,
    )


# ── Simplified Builder for Destructive Tools ──


def build_destructive_tool(
    name: str,
    description: str,
    input_schema: type[I],
    call_fn: CallFunction[I, O],
    *,
    is_concurrency_safe: bool = False,
    interrupt_behavior: str = "block",
) -> CallableTool[I, O]:
    """Convenience builder for destructive tools.

    Destructive tools require explicit confirmation and have strict defaults:
    - is_destructive=True
    - is_read_only=False
    - is_concurrency_safe=False (usually not safe)
    - interrupt_behavior='block' (don't interrupt destructive ops)

    Args:
        name: Tool name
        description: Tool description
        input_schema: Pydantic input model
        call_fn: Implementation function
        is_concurrency_safe: Override if tool is safe to run in parallel (default: False)
        interrupt_behavior: Override if tool can be interrupted (default: 'block')

    Returns:
        CallableTool configured for destructive operations

    Example:
        FileDeleteTool = build_destructive_tool(
            name="file_delete",
            description="Delete a file permanently",
            input_schema=FileDeleteInput,
            call_fn=delete_file_impl,
        )
    """
    return build_callable_tool(
        name=name,
        description=description,
        input_schema=input_schema,
        call_fn=call_fn,
        is_read_only=False,
        is_concurrency_safe=is_concurrency_safe,
        is_destructive=True,
        interrupt_behavior=interrupt_behavior,
    )
