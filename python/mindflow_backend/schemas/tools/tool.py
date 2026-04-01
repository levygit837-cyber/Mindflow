"""Unified tool interface for MindFlow.

Mirrors the Claude Code CLI Tool<T> pattern:
- Generic Tool[I, O] with Pydantic input schema
- Safe defaults: is_read_only=False, is_destructive=False, is_concurrency_safe=False
- Type-safe call signature: Tool[I, O].call(input: I, context: ToolContext) → O
- Execution mode derived from metadata (is_destructive → ACCEPTS_EDITS, etc.)

Design principles:
- Every tool has consistent metadata (name, description, execution_mode)
- Permission flags are explicit (no implicit behavior)
- Defaults are fail-closed (must opt-in to destructive/concurrent behavior)

Usage:
    @tool
    class FileReadTool:
        name = "FileReadTool"
        description = "Read file contents"
        input_schema = FileReadInput
        is_read_only = True  # → BYPASS mode

    # Or using build_tool() for quick definition:
    read_tool = build_tool(
        name="FileReadTool",
        description="Read file contents",
        input_schema=FileReadInput,
        execute=read_file_impl,
        is_read_only=True,
    )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from mindflow_backend.schemas.tools.base import ToolSchema
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.execution import ToolExecutionMode

if TYPE_CHECKING:
    from mindflow_backend.schemas.tools.context import ToolPermissionContext

# ---------------------------------------------------------------------------
# Type Variables
# ---------------------------------------------------------------------------

I = TypeVar("I", bound=dict[str, Any])  # Input: must be a dict (JSON-compatible)
O = TypeVar("O", bound=Any)  # Output: any JSON-serializable type


# ---------------------------------------------------------------------------
# Base Tool Interface (Generic)
# ---------------------------------------------------------------------------


class Tool(ABC, Generic[I, O]):
    """Unified tool interface — mirrors Claude Code's Tool<T>.

    Every tool must implement:
    - name: str            (unique identifier)
    - description: str     (shown to model and user)
    - input_schema: type   (Pydantic model for validation)
    - execute(input, context) → output

    Permission metadata is explicit and defaults to safe values:
    - is_read_only=False      (assume writes until proven otherwise)
    - is_destructive=False    (assume safe until specified)
    - is_concurrency_safe=False (assume stateful until confirmed)

    Execution mode is derived from metadata but can be overridden.
    """

    # -- Identity (required) --

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name — must be unique and match the name used in tool calls."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description — shown to the model and in the tool list."""

    @property
    @abstractmethod
    def input_schema(self) -> type[I]:
        """Pydantic model defining valid input for this tool."""

    # -- Execution (required) --

    @abstractmethod
    def execute(self, input: I, context: ToolContext) -> O:
        """Execute the tool with validated input.

        Args:
            input: Validated input dict (matches input_schema)
            context: Execution context (permissions, abort signal, etc.)

        Returns:
            Tool output (JSON-serializable or structured result)
        """

    # -- Permission Metadata (defaults to fail-closed) --

    @property
    def is_read_only(self) -> bool:
        """True if tool never modifies external state (files, network, etc.).

        Read-only tools can be allowed in strict/sandbox environments without
        risk of side effects.
        """
        return False

    @property
    def is_concurrency_safe(self) -> bool:
        """True if tool can be called concurrently without race conditions.

        Tools that write to shared state or depend on file ordering are NOT
        concurrency safe.
        """
        return False

    @property
    def is_destructive(self) -> bool:
        """True if tool performs irreversible operations (delete, overwrite, send).

        Destructive tools always require explicit user permission unless
        mode=bypass (sandbox only).
        """
        return False

    # This property is intentionally not marked @abstractmethod because
    # it has a default value. Subclasses can override but most won't need to.
    @property
    def is_enabled(self) -> bool:
        """True if tool is currently available for use."""
        return True

    # -- Execution Mode (derived from metadata, can be overridden) --

    @property
    def execution_mode(self) -> ToolExecutionMode:
        """How this tool is executed — derived from permission metadata.

        Default behavior:
        - is_destructive=True → ACCEPTS_EDITS (always requires permission)
        - is_read_only=True → BYPASS (no permission needed)
        - Neither set → ASK (interactive approval required)

        Override to customize execution behavior.
        """
        if self.is_destructive:
            return ToolExecutionMode.ACCEPTS_EDITS
        if self.is_read_only:
            return ToolExecutionMode.BYPASS
        return ToolExecutionMode.ASK

    # -- Schema Generation --

    def to_tool_schema(self) -> ToolSchema:
        """Convert to a ToolSchema for LLM tool definitions."""
        return ToolSchema(
            name=self.name,
            description=self.description,
        )


# ---------------------------------------------------------------------------
# Decorator: @tool class registration
# ---------------------------------------------------------------------------


def tool(cls: type) -> type:
    """Decorator to mark a class as a MindFlow tool.

    Validates that the class implements the Tool interface correctly:
    - All required @abstractmethod/@property methods are defined
    - input_schema is a Pydantic BaseModel
    """
    # Check required properties
    for attr in ("name", "description", "input_schema", "execute"):
        if not hasattr(cls, attr):
            raise TypeError(
                f"Tool class {cls.__name__!r} must define '{attr}' "
                f"(required by Tool interface)"
            )
    return cls


# ---------------------------------------------------------------------------
# Alias compatibility for code searching for 'Tool' by name
# ---------------------------------------------------------------------------

# ToolBase keeps backwards-compatible naming for code searching for this token.
ToolBase = Tool