"""Tool execution context — integrates with permission system.

Mirrors Claude Code's ToolUseContext (from Tool.ts) extended with
PermissionManager integration.

Design principles:
- ToolContext carries PermissionContext for runtime permission checks
- Abstracts abort/cancellation signaling
- Provides access to AppState for tool-internal state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from mindflow_backend.permissions.types import PermissionContext, PermissionResult

if TYPE_CHECKING:
    from mindflow_backend.permissions.manager import PermissionManager

# Alias for backwards compatibility
ToolPermissionContext = PermissionContext


@dataclass
class ToolContext:
    """Context available during tool execution.

    Similar to Claude Code's ToolUseContext — provides access to:
    - Permission state (PermissionContext + PermissionManager)
    - Abort signal for cancellation
    - AppState for reading/writing tool-internal state

    Usage:
        class MyTool(Tool):
            async def execute(self, input: dict, context: ToolContext) -> Result:
                # Check permission before executing
                result = context.check_permission("MyTool", input)
                if not result.is_allow:
                    return result
                # ... execute tool logic
    """

    # Permission system integration
    permission_context: PermissionContext
    permission_manager: Any | None = None  # PermissionManager | None

    # Cancellation support
    abort_signal: Any = None  # threading.Event, asyncio.Event, or callable
    abort_callback: Callable[[], bool] | None = None

    # Tool execution state
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_use_id: str | None = None

    # AppState access (for tools that need to read/write internal state)
    get_state: Callable[[], Any] | None = None
    set_state: Callable[[Any], None] | None = None

    @property
    def is_aborted(self) -> bool:
        """Check if execution should be cancelled."""
        if self.abort_callback:
            return self.abort_callback()
        if self.abort_signal is None:
            return False
        if callable(self.abort_signal):
            return self.abort_signal()
        if hasattr(self.abort_signal, "is_set"):
            return self.abort_signal.is_set()
        return bool(self.abort_signal)

    def check_permission(
        self,
        tool_name: str | None = None,
        input: dict[str, Any] | None = None,
        tool_content: str | None = None,
    ) -> PermissionResult:
        """Check permissions for the current tool.

        Delegates to PermissionManager if available, otherwise returns ALLOW.

        Args:
            tool_name: Tool name (defaults to context metadata)
            input: Validated tool input
            tool_content: Extracted content for pattern matching

        Returns:
            PermissionResult with allow/deny/ask decision
        """
        if self.permission_manager is None:
            return PermissionResult(
                behavior="allow",
                reason=None,
            )

        import asyncio

        name = tool_name or self.metadata.get("tool_name", "unknown")
        tool_input = input or self.metadata.get("tool_input", {})

        # Run async permission check in sync context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're in async context, create task
            raise RuntimeError(
                "check_permission() called from async context. "
                "Use await check_permission_async() instead."
            )

        # Sync execution: run in new event loop
        import asyncio as _asyncio
        return _asyncio.run(
            self.permission_manager.check_permission(
                tool_name=name,
                input=tool_input,
                context=self.permission_context,
                tool_content=tool_content,
                tool_use_id=self.tool_use_id,
            )
        )

    async def check_permission_async(
        self,
        tool_name: str | None = None,
        input: dict[str, Any] | None = None,
        tool_content: str | None = None,
    ) -> PermissionResult:
        """Async version of check_permission()."""
        if self.permission_manager is None:
            return PermissionResult(behavior="allow")

        name = tool_name or self.metadata.get("tool_name", "unknown")
        tool_input = input or self.metadata.get("tool_input", {})

        return await self.permission_manager.check_permission(
            tool_name=name,
            input=tool_input,
            context=self.permission_context,
            tool_content=tool_content,
            tool_use_id=self.tool_use_id,
        )

    def get_app_state(self) -> Any | None:
        """Get current application state."""
        if self.get_state:
            return self.get_state()
        return None

    def set_app_state(self, state: Any) -> None:
        """Update application state."""
        if self.set_state:
            self.set_state(state)


# Helper functions for creating common permission contexts
def sandbox_context(
    session_id: str,
    user_id: str | None = None,
    allowed_paths: list[str] | None = None,
) -> PermissionContext:
    """Create a sandboxed permission context with restricted file access."""
    return PermissionContext(
        session_id=session_id,
        user_id=user_id,
        mode="prompt",
        allowed_paths=allowed_paths or [],
        metadata={"sandbox": True},
    )


def strict_context(
    session_id: str,
    user_id: str | None = None,
) -> PermissionContext:
    """Create a strict permission context that prompts for all operations."""
    return PermissionContext(
        session_id=session_id,
        user_id=user_id,
        mode="prompt",
        metadata={"strict": True},
    )


def read_only_context(
    session_id: str,
    user_id: str | None = None,
) -> PermissionContext:
    """Create a read-only permission context that denies write operations."""
    return PermissionContext(
        session_id=session_id,
        user_id=user_id,
        mode="prompt",
        metadata={"read_only": True},
    )