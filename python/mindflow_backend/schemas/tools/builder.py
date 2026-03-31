"""Tool builder factory for MindFlow.

Mirrors the Claude Code CLI buildTool() pattern:
- Safe defaults: is_read_only=False, is_destructive=False, is_concurrency_safe=False
- Only required: name, description, input_schema, execute
- Fail-closed: tools without explicit permission flags are treated as ASK mode

Usage:
    # Minimal — all defaults are fail-closed
    tool = build_tool(
        name="MyTool",
        description="Does something useful",
        input_schema=MyInput,
        execute=my_handler,
        is_read_only=True,
    )

    # Explicit — destructive tool (always requires permission)
    write_tool = build_tool(
        name="FileWriteTool",
        description="Write to a file",
        input_schema=FileWriteInput,
        execute=write_file,
        is_destructive=True,
    )
"""

from __future__ import annotations

from typing import Any, Callable

from mindflow_backend.schemas.tools.execution import ToolExecutionMode
from mindflow_backend.schemas.tools.tool import Tool, ToolContext

# ---------------------------------------------------------------------------
# Type Variables (local — avoids circular import with tool.py)
# ---------------------------------------------------------------------------

I = Any  # Input: dict[str, Any] (JSON-compatible)
O = Any  # Output: JSON-serializable

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# These MUST match the defaults in Tool class properties.
TOOL_DEFAULTS = {
    "is_read_only": False,
    "is_concurrency_safe": False,
    "is_destructive": False,
    "is_enabled": True,
}


# ---------------------------------------------------------------------------
# Tool Builder
# ---------------------------------------------------------------------------


def build_tool(
    name: str,
    description: str,
    input_schema: type[dict[str, Any]],
    execute: Callable[[I, ToolContext], O],
    *,
    is_read_only: bool | None = None,
    is_concurrency_safe: bool | None = None,
    is_destructive: bool | None = None,
    is_enabled: bool | None = None,
    execution_mode: ToolExecutionMode | None = None,
) -> Tool:
    """Create a tool with safe defaults — mirrors Claude Code's buildTool().

    All permission flags default to fail-closed (False) unless explicitly set.
    This ensures that:
    - New tools don't accidentally write/modify state
    - Read-only tools must opt-in with is_read_only=True
    - Destructive tools must opt-in with is_destructive=True

    Args:
        name: Tool name (unique identifier for tool calls)
        description: Tool description (shown to model and user)
        input_schema: Pydantic model defining valid input
        execute: Callable that takes (input, context) → output
        is_read_only: True if tool never modifies state (→ BYPASS mode)
        is_concurrency_safe: True if tool can run concurrently
        is_destructive: True if tool performs irreversible ops (→ ACCEPTS_EDITS)
        is_enabled: True if tool is available (default True)
        execution_mode: Override derived mode (usually derived from metadata)

    Returns:
        Concrete Tool instance with all defaults applied
    """
    # Apply defaults for None values
    tool_read_only = is_read_only if is_read_only is not None else TOOL_DEFAULTS["is_read_only"]
    tool_concurrent = is_concurrency_safe if is_concurrency_safe is not None else TOOL_DEFAULTS["is_concurrency_safe"]
    tool_destructive = is_destructive if is_destructive is not None else TOOL_DEFAULTS["is_destructive"]
    tool_enabled = is_enabled if is_enabled is not None else TOOL_DEFAULTS["is_enabled"]

    return _ConcreteTool(
        name=name,
        description=description,
        input_schema=input_schema,
        execute_fn=execute,
        is_read_only=tool_read_only,
        is_concurrency_safe=tool_concurrent,
        is_destructive=tool_destructive,
        is_enabled=tool_enabled,
        execution_mode=execution_mode,
    )


# ---------------------------------------------------------------------------
# Concrete Tool Implementation (internal)
# ---------------------------------------------------------------------------


class _ConcreteTool(Tool):
    """Concrete Tool implementation populated by build_tool().

    This class overrides the non-abstractmethod properties to allow
    runtime-defined values from build_tool().
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: type[dict[str, Any]],
        execute_fn: Callable[[I, ToolContext], O],
        is_read_only: bool = False,
        is_concurrency_safe: bool = False,
        is_destructive: bool = False,
        is_enabled: bool = True,
        execution_mode: ToolExecutionMode | None = None,
    ) -> None:
        self._name = name
        self._description = description
        self._input_schema = input_schema
        self._execute_fn = execute_fn
        self._is_read_only = is_read_only
        self._is_concurrency_safe = is_concurrency_safe
        self._is_destructive = is_destructive
        self._is_enabled = is_enabled
        self._execution_mode = execution_mode

    # -- Required interface implementation --

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> type[dict[str, Any]]:
        return self._input_schema

    def execute(self, input: I, context: ToolContext) -> O:
        return self._execute_fn(input, context)

    # -- Permission metadata overrides --

    @property
    def is_read_only(self) -> bool:
        return self._is_read_only

    @property
    def is_concurrency_safe(self) -> bool:
        return self._is_concurrency_safe

    @property
    def is_destructive(self) -> bool:
        return self._is_destructive

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @property
    def execution_mode(self) -> ToolExecutionMode:
        if self._execution_mode is not None:
            return self._execution_mode
        # Fall back to parent's derived behavior
        return super().execution_mode