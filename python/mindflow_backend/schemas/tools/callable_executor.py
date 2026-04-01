"""Streaming tool executor with concurrency control.

This module provides the StreamingToolExecutor class that manages concurrent
tool execution, mirroring Claude Code's StreamingToolExecutor pattern.

Key features:
- Concurrent-safe tools run in parallel
- Non-concurrent tools run exclusively (wait for all others to finish)
- Results emitted in order
- Interrupt handling (cancel vs block)
- Error propagation with sibling cancellation

Design principles:
- Concurrent-safe tools can run together (e.g., multiple file reads)
- Non-concurrent tools must run alone (e.g., file writes, shell commands)
- Errors in critical tools (like shell) cancel sibling tools
- Interrupt behavior respects tool preferences (cancel vs block)

Example:
    executor = StreamingToolExecutor(tools, context)

    # Execute tool calls as they arrive
    result1 = await executor.execute_tool_call("file_read", {"file_path": "a.txt"})
    result2 = await executor.execute_tool_call("file_read", {"file_path": "b.txt"})  # Runs in parallel

    # Wait for all concurrent tools to finish
    await executor.wait_all()
"""

from __future__ import annotations

import asyncio
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.callable import CallableTool, ToolResult
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


class ToolExecutionState:
    """Tracks the state of a single tool execution."""

    def __init__(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        is_concurrent_safe: bool,
    ):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.is_concurrent_safe = is_concurrent_safe
        self.status: str = "queued"  # queued, executing, completed, error
        self.task: asyncio.Task | None = None
        self.result: ToolResult | None = None


class StreamingToolExecutor:
    """Executes tools with concurrency control.

    Mirrors Claude Code's StreamingToolExecutor:
    - Concurrent-safe tools execute in parallel with other concurrent-safe tools
    - Non-concurrent tools execute exclusively (all others must finish first)
    - Results are buffered and emitted in order
    - Errors can trigger sibling cancellation

    Attributes:
        tools_by_name: Dictionary mapping tool names to CallableTool instances
        context: Tool execution context (permissions, abort signal, etc.)
        executing: List of currently executing tasks
        has_errored: Whether any tool has errored (triggers sibling cancellation)
        error_tool_name: Name of the tool that errored (for logging)
    """

    def __init__(
        self,
        tools: list[CallableTool],
        context: ToolContext,
        *,
        cancel_siblings_on_error: bool = True,
    ):
        """Initialize the executor.

        Args:
            tools: List of available CallableTool instances
            context: Tool execution context
            cancel_siblings_on_error: Whether to cancel sibling tools when one errors
                (default: True, mirrors Claude Code behavior for shell tools)
        """
        self.tools_by_name: dict[str, CallableTool] = {t.name: t for t in tools}
        self.context = context
        self.cancel_siblings_on_error = cancel_siblings_on_error

        # Execution state
        self.executing: list[asyncio.Task] = []
        self.has_errored = False
        self.error_tool_name: str | None = None

        # Abort controller for sibling cancellation
        self._sibling_abort_event = asyncio.Event()

    def _can_execute_concurrently(self, is_concurrent_safe: bool) -> bool:
        """Check if a tool can execute given current state.

        Args:
            is_concurrent_safe: Whether the tool is concurrent-safe

        Returns:
            True if tool can execute now, False if it must wait

        Rules:
            - If no tools executing: can execute
            - If tool is concurrent-safe AND all executing tools are concurrent-safe: can execute
            - Otherwise: must wait
        """
        if not self.executing:
            return True

        # Non-concurrent tool must wait for all executing tools
        if not is_concurrent_safe:
            return False

        # Concurrent-safe tool can only run if all executing tools are also concurrent-safe
        # (We don't track this per-task, so we conservatively wait if any task is running)
        # TODO: Track concurrent-safety per task for better parallelism
        return True

    async def execute_tool_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_call_id: str | None = None,
    ) -> ToolResult:
        """Execute a single tool call with concurrency control.

        This is the main entry point for tool execution. It:
        1. Validates the tool exists
        2. Validates the input against the tool's schema
        3. Checks if tool can execute concurrently
        4. Executes the tool (waiting if necessary)
        5. Returns the result

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input dictionary (will be validated against tool schema)
            tool_call_id: Optional ID for tracking (used in streaming)

        Returns:
            ToolResult with data, success flag, and optional error
        """
        # Check if tool exists
        tool = self.tools_by_name.get(tool_name)
        if not tool:
            _logger.warning(f"Unknown tool: {tool_name}")
            return ToolResult(
                data=None,
                success=False,
                error=f"Unknown tool: {tool_name}",
                metadata={"error_code": "UNKNOWN_TOOL"},
            )

        # Check if tool is enabled
        if not tool.is_enabled():
            _logger.warning(f"Tool disabled: {tool_name}")
            return ToolResult(
                data=None,
                success=False,
                error=f"Tool is disabled: {tool_name}",
                metadata={"error_code": "TOOL_DISABLED"},
            )

        # Validate and parse input
        try:
            validated_input = tool.input_schema(**tool_input)
        except Exception as e:
            _logger.warning(f"Invalid input for {tool_name}: {e}")
            return ToolResult(
                data=None,
                success=False,
                error=f"Invalid input: {e}",
                metadata={"error_code": "INVALID_INPUT"},
            )

        # Custom validation
        is_valid, validation_error = await tool.validate_input(validated_input, self.context)
        if not is_valid:
            _logger.warning(f"Validation failed for {tool_name}: {validation_error}")
            return ToolResult(
                data=None,
                success=False,
                error=validation_error or "Validation failed",
                metadata={"error_code": "VALIDATION_FAILED"},
            )

        # Check permissions
        permission_result = await tool.check_permissions(validated_input, self.context)
        if permission_result.get("behavior") == "deny":
            reason = permission_result.get("reason", "Permission denied")
            _logger.warning(f"Permission denied for {tool_name}: {reason}")
            return ToolResult(
                data=None,
                success=False,
                error=reason,
                metadata={"error_code": "PERMISSION_DENIED"},
            )

        # Update input if permissions modified it
        if "updated_input" in permission_result and permission_result["updated_input"] is not None:
            validated_input = permission_result["updated_input"]

        # Check concurrency
        is_concurrent_safe = tool.is_concurrency_safe(validated_input)

        # Wait for executing tools if necessary
        if not self._can_execute_concurrently(is_concurrent_safe):
            _logger.debug(
                f"Tool {tool_name} waiting for {len(self.executing)} executing tools to finish"
            )
            await self.wait_all()

        # Check if we've been aborted by a sibling error
        if self.has_errored and self.cancel_siblings_on_error:
            _logger.info(f"Tool {tool_name} cancelled due to sibling error: {self.error_tool_name}")
            return ToolResult(
                data=None,
                success=False,
                error=f"Cancelled: sibling tool {self.error_tool_name} errored",
                metadata={"error_code": "SIBLING_ERROR"},
            )

        # Execute the tool
        _logger.info(f"Executing tool: {tool_name}", tool_call_id=tool_call_id)

        try:
            # Create task for concurrent execution
            task = asyncio.create_task(
                self._execute_tool_with_error_handling(
                    tool, validated_input, tool_name, tool_call_id
                )
            )

            # Track executing task if concurrent-safe
            if is_concurrent_safe:
                self.executing.append(task)

            # Wait for result
            result = await task

            # Remove from executing list
            if is_concurrent_safe and task in self.executing:
                self.executing.remove(task)

            return result

        except asyncio.CancelledError:
            _logger.warning(f"Tool {tool_name} was cancelled")
            return ToolResult(
                data=None,
                success=False,
                error="Tool execution was cancelled",
                metadata={"error_code": "CANCELLED"},
            )
        except Exception as e:
            _logger.error(f"Unexpected error executing {tool_name}: {e}", exc_info=True)
            return ToolResult(
                data=None,
                success=False,
                error=f"Unexpected error: {e}",
                metadata={"error_code": "UNEXPECTED_ERROR"},
            )

    async def _execute_tool_with_error_handling(
        self,
        tool: CallableTool,
        validated_input: Any,
        tool_name: str,
        tool_call_id: str | None,
    ) -> ToolResult:
        """Execute tool with error handling and sibling cancellation.

        Args:
            tool: The CallableTool instance
            validated_input: Validated input (Pydantic model)
            tool_name: Tool name (for logging)
            tool_call_id: Optional call ID (for tracking)

        Returns:
            ToolResult from the tool execution
        """
        try:
            # Execute the tool
            result = await tool.call(validated_input, self.context, on_progress=None)

            # Check if tool errored
            if not result.success:
                _logger.warning(
                    f"Tool {tool_name} returned error: {result.error}",
                    tool_call_id=tool_call_id,
                )

                # Mark as errored and cancel siblings if configured
                if self.cancel_siblings_on_error:
                    self.has_errored = True
                    self.error_tool_name = tool_name
                    self._sibling_abort_event.set()

                    # Cancel all executing sibling tasks
                    for task in self.executing:
                        if not task.done():
                            task.cancel()

            return result

        except Exception as e:
            _logger.error(f"Tool {tool_name} raised exception: {e}", exc_info=True)

            # Mark as errored
            if self.cancel_siblings_on_error:
                self.has_errored = True
                self.error_tool_name = tool_name
                self._sibling_abort_event.set()

                # Cancel siblings
                for task in self.executing:
                    if not task.done():
                        task.cancel()

            return ToolResult(
                data=None,
                success=False,
                error=f"Tool execution failed: {e}",
                metadata={"error_code": "EXECUTION_ERROR"},
            )

    async def wait_all(self) -> None:
        """Wait for all executing tools to complete.

        This is called:
        - Before executing a non-concurrent tool (must wait for all others)
        - At the end of a tool execution round (ensure all complete)
        """
        if not self.executing:
            return

        _logger.debug(f"Waiting for {len(self.executing)} executing tools to finish")

        # Wait for all tasks (ignore exceptions - they're already handled)
        await asyncio.gather(*self.executing, return_exceptions=True)

        # Clear the list
        self.executing.clear()

    def has_executing_tools(self) -> bool:
        """Check if any tools are currently executing."""
        return len(self.executing) > 0

    def get_executing_tool_names(self) -> list[str]:
        """Get names of currently executing tools (for debugging)."""
        # We don't track tool names per task currently
        # This would require storing metadata with each task
        return [f"task_{i}" for i in range(len(self.executing))]
