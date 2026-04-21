"""Callable tool interface - mirrors Claude Code pattern.

This module provides a callable-first tool interface that eliminates the need
for LangChain wrappers. Tools implement a `call()` method instead of `execute()`,
enabling direct invocation with proper type safety and concurrency control.

Key differences from execute() pattern:
- call() is the primary method (not execute())
- Returns ToolResult[O] (not dict)
- Supports progress callbacks
- Supports interrupt behavior
- Built-in concurrency control metadata

Example:
    async def read_file_impl(input: FileReadInput, ctx: ToolContext) -> ToolResult[str]:
        content = await read_file(input.file_path)
        return ToolResult(data=content)

    read_tool = build_callable_tool(
        name="file_read",
        description="Read file contents",
        input_schema=FileReadInput,
        call_fn=read_file_impl,
        is_read_only=True,
        is_concurrency_safe=True,
    )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Generic, TypeVar

from pydantic import BaseModel

from mindflow_backend.schemas.tools.context import ToolContext

# Type variables for generic tool interface
I = TypeVar("I", bound=BaseModel)  # Input must be Pydantic model
O = TypeVar("O")  # Output can be any JSON-serializable type


class ToolResult(Generic[O]):
    """Result of a tool execution.

    Wraps the tool output with success/error metadata and optional
    additional context.

    Attributes:
        data: The actual result data (None if error)
        success: Whether execution succeeded
        error: Error message if failed (None if success)
        metadata: Additional context (timing, warnings, etc.)
    """

    def __init__(
        self,
        data: O | None = None,
        success: bool = True,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.data = data
        self.success = success
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "data": self.data,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        if self.success:
            return f"ToolResult(success=True, data={self.data!r})"
        return f"ToolResult(success=False, error={self.error!r})"


CallableToolResult = ToolResult


def _callable_result_from_dict(
    data: dict[str, Any] | None,
    success: bool,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolResult[dict[str, Any]]:
    """Backwards-compatible helper for callable tools that return dictionaries."""
    return ToolResult(
        data=data if success else None,
        success=success,
        error=error,
        metadata=metadata or {},
    )


def build_callable_tool(*args, **kwargs):
    """Compatibility proxy to the callable tool builder module."""
    from mindflow_backend.schemas.tools.callable_builder import build_callable_tool as _builder

    return _builder(*args, **kwargs)


def build_readonly_tool(*args, **kwargs):
    """Compatibility proxy to the read-only callable tool builder."""
    from mindflow_backend.schemas.tools.callable_builder import build_readonly_tool as _builder

    return _builder(*args, **kwargs)


def build_destructive_tool(*args, **kwargs):
    """Compatibility proxy to the destructive callable tool builder."""
    from mindflow_backend.schemas.tools.callable_builder import build_destructive_tool as _builder

    return _builder(*args, **kwargs)


# Type alias for progress callback
ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


class CallableTool(ABC, Generic[I, O]):
    """Callable tool interface - mirrors Claude Code Tool<I, O>.

    This is the primary tool interface for MindFlow. Tools implement the
    `call()` method which is invoked directly by the runtime without
    requiring LangChain wrappers.

    Type Parameters:
        I: Input type (must be a Pydantic BaseModel)
        O: Output type (any JSON-serializable type)

    Required Properties:
        - name: Unique tool identifier
        - description: Human-readable description
        - input_schema: Pydantic model for input validation

    Required Methods:
        - call(): Execute the tool with validated input

    Optional Methods (with safe defaults):
        - is_read_only(): Whether tool modifies state
        - is_concurrency_safe(): Whether tool can run in parallel
        - is_destructive(): Whether tool performs irreversible ops
        - is_enabled(): Whether tool is available
        - interrupt_behavior(): How to handle user interrupts
        - validate_input(): Custom input validation
        - check_permissions(): Permission checking
    """

    # ── Required Properties ──

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (unique identifier for tool calls)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description (shown to model and user)."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> type[I]:
        """Pydantic model for input validation.

        The model defines the expected input structure and is used
        for automatic validation before call() is invoked.
        """
        ...

    # ── Primary Method (CALLABLE PATTERN) ──

    @abstractmethod
    async def call(
        self,
        input: I,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult[O]:
        """Execute tool with validated input and context.

        This is the PRIMARY method that replaces execute(). It receives
        already-validated input (Pydantic model instance) and returns
        a ToolResult with the output data.

        Args:
            input: Validated input (Pydantic model instance)
            context: Tool execution context (permissions, metadata, abort signal)
            on_progress: Optional callback for progress updates

        Returns:
            ToolResult with data, success flag, and optional error

        Example:
            async def call(self, input: FileReadInput, context: ToolContext) -> ToolResult[str]:
                try:
                    content = await read_file(input.file_path)
                    return ToolResult(data=content, success=True)
                except FileNotFoundError as e:
                    return ToolResult(data=None, success=False, error=str(e))
        """
        ...

    # ── Metadata (with safe defaults) ──

    def is_read_only(self, input: I) -> bool:
        """True if tool never modifies state (files, DB, external systems).

        Read-only tools can bypass certain permission checks and are
        safe to run speculatively.

        Default: False (fail-closed - assume tool writes)
        """
        return False

    def is_concurrency_safe(self, input: I) -> bool:
        """True if tool can run concurrently with other tools.

        Concurrent-safe tools can execute in parallel with other
        concurrent-safe tools. Non-concurrent tools must run exclusively.

        Default: False (fail-closed - assume not safe)

        Examples of concurrent-safe tools:
        - file_read (if different files)
        - http_client (independent requests)
        - grep_search (read-only)

        Examples of non-concurrent tools:
        - file_write (race conditions)
        - shell_executor (shared state)
        - database_transaction (isolation)
        """
        return False

    def is_destructive(self, input: I) -> bool:
        """True if tool performs irreversible operations.

        Destructive tools require explicit user confirmation and
        cannot be undone (delete, overwrite, send, publish).

        Default: False

        Examples:
        - file_delete (cannot undo)
        - email_send (cannot unsend)
        - database_drop (data loss)
        """
        return False

    def is_enabled(self) -> bool:
        """True if tool is available for use.

        Can be used to disable tools based on configuration,
        feature flags, or runtime conditions.

        Default: True
        """
        return True

    def interrupt_behavior(self) -> str:
        """How to handle user interrupts: 'cancel' or 'block'.

        - 'cancel': Stop execution and discard result when user interrupts
        - 'block': Keep running; new message waits for completion

        Default: 'block' (safe - don't lose work)

        Use 'cancel' for:
        - Read-only operations (safe to retry)
        - Long-running searches (user can refine query)
        - Speculative operations (not critical)

        Use 'block' for:
        - Write operations (avoid partial writes)
        - Transactions (maintain consistency)
        - Critical operations (must complete)
        """
        return "block"

    # ── Validation & Permissions ──

    async def validate_input(
        self,
        input: I,
        context: ToolContext,
    ) -> tuple[bool, str | None]:
        """Validate input before execution (beyond Pydantic validation).

        Use this for validation that requires context or async operations:
        - File existence checks
        - Permission verification
        - Resource availability
        - Business logic validation

        Args:
            input: Validated Pydantic input
            context: Tool execution context

        Returns:
            (is_valid, error_message)
            - (True, None) if valid
            - (False, "error message") if invalid

        Example:
            async def validate_input(self, input: FileReadInput, context: ToolContext):
                if not await file_exists(input.file_path):
                    return (False, f"File not found: {input.file_path}")
                return (True, None)
        """
        return (True, None)

    async def check_permissions(
        self,
        input: I,
        context: ToolContext,
    ) -> dict[str, Any]:
        """Check if tool execution is allowed.

        This is called after validate_input() passes. Use it to:
        - Check user permissions
        - Verify access control
        - Apply security policies
        - Modify input based on permissions

        Args:
            input: Validated input
            context: Tool execution context (includes permission_context)

        Returns:
            Dictionary with:
            {
                "behavior": "allow" | "deny" | "ask",
                "reason": str | None,
                "updated_input": I | None,  # Modified input if needed
            }

        Example:
            async def check_permissions(self, input: FileWriteInput, context: ToolContext):
                if input.file_path.startswith("/etc/"):
                    return {
                        "behavior": "deny",
                        "reason": "Cannot write to /etc/ directory",
                    }
                return {"behavior": "allow", "updated_input": input}
        """
        return {"behavior": "allow", "updated_input": input}

    # ── Helper Methods ──

    def get_metadata(self) -> dict[str, Any]:
        """Get tool metadata for introspection.

        Returns a dictionary with all tool metadata that can be
        used for tool discovery, filtering, and UI display.
        """
        return {
            "name": self.name,
            "description": self.description,
            "is_read_only": self.is_read_only,
            "is_concurrency_safe": self.is_concurrency_safe,
            "is_destructive": self.is_destructive,
            "is_enabled": self.is_enabled(),
            "interrupt_behavior": self.interrupt_behavior(),
        }

    def __repr__(self) -> str:
        return f"CallableTool(name={self.name!r})"
