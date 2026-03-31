"""Claude Code-style hook system with input mutation support.

Inspired by Claude Code's toolHooks.ts and hooks.ts implementation.
This module provides:
- PreToolUse hooks with input mutation capability
- PostToolUse hooks with feedback loop and retry
- PermissionRequest hooks for programmatic approval/denial
- PostToolUseFailure hooks with recovery suggestions
- AsyncGenerator pattern for hook execution
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.hooks.types import HookEvent

_logger = get_logger(__name__)


class PermissionBehavior(str, Enum):
    """Behavior returned by permission hooks."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    PASSTHROUGH = "passthrough"  # Let normal permission flow continue


class HookOutcome(str, Enum):
    """Outcome of a hook execution."""

    SUCCESS = "success"
    BLOCKING = "blocking"
    NON_BLOCKING_ERROR = "non_blocking_error"
    CANCELLED = "cancelled"


@dataclass
class HookResult:
    """Result from a single hook execution.

    Inspired by Claude Code's HookResult interface.
    """

    outcome: HookOutcome = HookOutcome.SUCCESS
    # Blocking error (stops execution)
    blocking_error: str | None = None
    # Non-blocking error message
    error_message: str | None = None
    # Permission behavior (PreToolUse only)
    permission_behavior: PermissionBehavior | None = None
    # Modified tool input (input mutation)
    updated_input: dict[str, Any] | None = None
    # Prevent continuation of execution
    prevent_continuation: bool = False
    # Stop reason (for stop hooks)
    stop_reason: str | None = None
    # Additional context to append
    additional_context: str | None = None
    # Retry request (for PostToolUseFailure)
    retry: bool = False


@dataclass
class AggregatedHookResult:
    """Aggregated result from multiple hooks.

    Inspired by Claude Code's AggregatedHookResult interface.
    """

    messages: list[str] = field(default_factory=list)
    blocking_error: str | None = None
    permission_result: dict[str, Any] | None = None
    updated_input: dict[str, Any] | None = None
    prevent_continuation: bool = False
    stop_reason: str | None = None
    additional_contexts: list[str] = field(default_factory=list)
    permission_request_result: dict[str, Any] | None = None
    retry: bool = False
    # Raw results from individual hooks
    raw_results: list[HookResult] = field(default_factory=list)


class ClaudeStyleHookManager:
    """Manager for Claude Code-style hooks with input mutation.

    Key features:
    - PreToolUse hooks can modify tool input before execution
    - PostToolUse hooks can provide feedback and suggest retries
    - PermissionRequest hooks enable programmatic permission management
    - All hooks use async generators for streaming progress

    Usage:
        manager = ClaudeStyleHookManager()

        # Register a PreToolUse hook
        @manager.register_hook(HookEvent.PRE_TOOL_USE, "bash")
        async def validate_bash_command(tool_input: dict) -> AsyncGenerator[HookResult, None]:
            if "rm -rf" in tool_input.get("command", ""):
                yield HookResult(
                    permission_behavior=PermissionBehavior.DENY,
                    blocking_error="Destructive command blocked",
                )
            else:
                yield HookResult(
                    updated_input={"command": tool_input["command"] + " 2>&1"},
                )

        # Execute hooks
        async for result in manager.execute_pre_tool_use_hooks("bash", {...}):
            if result.blocking_error:
                # Handle blocking error
                pass
            if result.updated_input:
                # Use modified input
                pass
    """

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, dict[str, list[Callable]]] = {
            HookEvent.PRE_TOOL_USE: {},
            HookEvent.POST_TOOL_USE: {},
            HookEvent.PRE_TOOL_USE_FAILURE: {},
            HookEvent.POST_TOOL_USE_FAILURE: {},
            HookEvent.PERMISSION_REQUEST: {},
            HookEvent.QUERY_START: {"global": []},
            HookEvent.STOP: {"global": []},
        }
        self._enabled = True

    def register_hook(
        self,
        event: HookEvent,
        tool_name: str = "*",
    ) -> Callable:
        """Decorator to register a hook function.

        Args:
            event: Hook event type.
            tool_name: Tool name to match (use "*" for all tools).

        Returns:
            Decorator function.
        """
        def decorator(fn: Callable) -> Callable:
            if tool_name == "*":
                tool_name = "global"
            hooks_for_event = self._hooks.get(event, {})
            if tool_name not in hooks_for_event:
                hooks_for_event[tool_name] = []
            hooks_for_event[tool_name].append(fn)
            self._hooks[event] = hooks_for_event
            return fn
        return decorator

    def enable(self) -> None:
        """Enable hook execution."""
        self._enabled = True

    def disable(self) -> None:
        """Disable hook execution."""
        self._enabled = False

    def clear_hooks(self, event: HookEvent | None = None, tool_name: str | None = None) -> None:
        """Clear registered hooks.

        Args:
            event: Specific event to clear (None for all).
            tool_name: Specific tool to clear (None for all).
        """
        if event is None:
            for evt in self._hooks:
                self._hooks[evt] = {"global": []}
            return

        if event in self._hooks:
            if tool_name is None:
                self._hooks[event] = {tool_name or "global": []}
            elif tool_name in self._hooks[event]:
                self._hooks[event][tool_name] = []

    async def execute_pre_tool_use_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[AggregatedHookResult, None]:
        """Execute PreToolUse hooks with input mutation support.

        This is the key differentiator from the existing MindFlow hooks:
        hooks can modify tool_input, and subsequent hooks see the modified input.

        Args:
            tool_name: Name of the tool being executed.
            tool_input: Input parameters for the tool.
            tool_use_id: Unique ID for this tool use.
            context: Additional context for hook execution.

        Yields:
            AggregatedHookResult with hook outcomes.
        """
        if not self._enabled:
            return

        start_time = time.time()
        current_input = dict(tool_input)
        raw_results: list[HookResult] = []

        hooks = self._get_matching_hooks(HookEvent.PRE_TOOL_USE, tool_name)

        for hook_fn in hooks:
            try:
                async for hook_result in hook_fn(
                    tool_name=tool_name,
                    tool_input=current_input,
                    tool_use_id=tool_use_id,
                    context=context or {},
                ):
                    raw_results.append(hook_result)

                    # Aggregate results
                    if hook_result.blocking_error:
                        yield AggregatedHookResult(
                            blocking_error=hook_result.blocking_error,
                            permission_behavior=hook_result.permission_behavior,
                            raw_results=list(raw_results),
                        )
                        return

                    if hook_result.permission_behavior == PermissionBehavior.DENY:
                        yield AggregatedHookResult(
                            permission_result={
                                "behavior": "deny",
                                "reason": hook_result.blocking_error or "Denied by hook",
                            },
                            raw_results=list(raw_results),
                        )
                        return

                    if hook_result.permission_behavior == PermissionBehavior.ASK:
                        yield AggregatedHookResult(
                            permission_result={
                                "behavior": "ask",
                                "message": hook_result.blocking_error or "Permission required",
                            },
                            raw_results=list(raw_results),
                        )
                        return

                    # Input mutation: update current_input for next hooks
                    if hook_result.updated_input is not None:
                        current_input = dict(hook_result.updated_input)
                        _logger.debug(
                            "hook_input_mutated",
                            tool_name=tool_name,
                            hook=hook_fn.__name__,
                            new_input_keys=list(current_input.keys()),
                        )

                    if hook_result.prevent_continuation:
                        yield AggregatedHookResult(
                            prevent_continuation=True,
                            stop_reason=hook_result.stop_reason,
                            raw_results=list(raw_results),
                        )
                        return

                    if hook_result.additional_context:
                        yield AggregatedHookResult(
                            additional_contexts=[hook_result.additional_context],
                            raw_results=list(raw_results),
                        )

                    # Passthrough: let normal execution continue
                    if hook_result.permission_behavior == PermissionBehavior.ALLOW:
                        yield AggregatedHookResult(
                            permission_result={"behavior": "allow"},
                            updated_input=current_input if current_input != tool_input else None,
                            raw_results=list(raw_results),
                        )

            except Exception as e:
                _logger.error(
                    "hook_execution_error",
                    tool_name=tool_name,
                    hook=hook_fn.__name__,
                    error=str(e),
                )
                raw_results.append(HookResult(
                    outcome=HookOutcome.NON_BLOCKING_ERROR,
                    error_message=str(e),
                ))

        # Final yield with any input mutations
        if current_input != tool_input:
            yield AggregatedHookResult(
                updated_input=current_input,
                raw_results=list(raw_results),
            )

    async def execute_post_tool_use_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_response: Any,
        tool_use_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[AggregatedHookResult, None]:
        """Execute PostToolUse hooks with feedback loop support.

        Hooks can:
        - Validate tool response
        - Suggest retry with different parameters
        - Add additional context based on response
        - Block execution if response is invalid

        Args:
            tool_name: Name of the tool that was executed.
            tool_input: Input that was passed to the tool.
            tool_response: Response from the tool.
            tool_use_id: Unique ID for this tool use.
            context: Additional context for hook execution.

        Yields:
            AggregatedHookResult with hook outcomes.
        """
        if not self._enabled:
            return

        raw_results: list[HookResult] = []

        hooks = self._get_matching_hooks(HookEvent.POST_TOOL_USE, tool_name)

        for hook_fn in hooks:
            try:
                async for hook_result in hook_fn(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_response=tool_response,
                    tool_use_id=tool_use_id,
                    context=context or {},
                ):
                    raw_results.append(hook_result)

                    if hook_result.blocking_error:
                        yield AggregatedHookResult(
                            blocking_error=hook_result.blocking_error,
                            raw_results=list(raw_results),
                        )
                        return

                    if hook_result.retry:
                        yield AggregatedHookResult(
                            retry=True,
                            raw_results=list(raw_results),
                        )

                    if hook_result.additional_context:
                        yield AggregatedHookResult(
                            additional_contexts=[hook_result.additional_context],
                            raw_results=list(raw_results),
                        )

            except Exception as e:
                _logger.error(
                    "post_hook_execution_error",
                    tool_name=tool_name,
                    hook=hook_fn.__name__,
                    error=str(e),
                )

        if raw_results:
            yield AggregatedHookResult(raw_results=list(raw_results))

    async def execute_permission_request_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[AggregatedHookResult, None]:
        """Execute PermissionRequest hooks for programmatic permission management.

        These hooks are called when a permission dialog would normally be
        displayed. Hooks can approve or deny the permission programmatically.

        Args:
            tool_name: Tool requesting permission.
            tool_input: Input that would be passed to the tool.
            tool_use_id: Unique ID for this tool use.
            context: Additional context for hook execution.

        Yields:
            AggregatedHookResult with permission decision.
        """
        if not self._enabled:
            return

        raw_results: list[HookResult] = []

        hooks = self._get_matching_hooks(HookEvent.PERMISSION_REQUEST, tool_name)

        for hook_fn in hooks:
            try:
                async for hook_result in hook_fn(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_use_id=tool_use_id,
                    context=context or {},
                ):
                    raw_results.append(hook_result)

                    if hook_result.permission_behavior:
                        yield AggregatedHookResult(
                            permission_result={
                                "behavior": hook_result.permission_behavior.value,
                                "hook": hook_fn.__name__,
                            },
                            raw_results=list(raw_results),
                        )
                        return

            except Exception as e:
                _logger.error(
                    "permission_hook_error:",
                    tool_name=tool_name,
                    hook=hook_fn.__name__,
                    error=str(e),
                )

        if raw_results:
            yield AggregatedHookResult(raw_results=list(raw_results))

    async def execute_post_tool_use_failure_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        error: str,
        tool_use_id: str = "",
        is_interrupt: bool = False,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[AggregatedHookResult, None]:
        """Execute PostToolUseFailure hooks with recovery suggestions.

        Hooks can:
        - Suggest retry with modified input
        - Provide alternative approaches
        - Block further execution
        - Log failure patterns

        Args:
            tool_name: Tool that failed.
            tool_input: Input that was passed.
            error: Error message from the failure.
            tool_use_id: Unique ID for this tool use.
            is_interrupt: Whether the tool was interrupted by user.
            context: Additional context for hook execution.

        Yields:
            AggregatedHookResult with hook outcomes.
        """
        if not self._enabled:
            return

        raw_results: list[HookResult] = []

        hooks = self._get_matching_hooks(HookEvent.POST_TOOL_USE_FAILURE, tool_name)

        for hook_fn in hooks:
            try:
                async for hook_result in hook_fn(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    error=error,
                    tool_use_id=tool_use_id,
                    is_interrupt=is_interrupt,
                    context=context or {},
                ):
                    raw_results.append(hook_result)

                    if hook_result.retry:
                        yield AggregatedHookResult(
                            retry=True,
                            updated_input=hook_result.updated_input,
                            raw_results=list(raw_results),
                        )
                        return

                    if hook_result.blocking_error:
                        yield AggregatedHookResult(
                            blocking_error=hook_result.blocking_error,
                            raw_results=list(raw_results),
                        )
                        return

            except Exception as e:
                _logger.error(
                    "failure_hook_error:",
                    tool_name=tool_name,
                    hook=hook_fn.__name__,
                    error=str(e),
                )

        if raw_results:
            yield AggregatedHookResult(raw_results=list(raw_results))

    def _get_matching_hooks(
        self,
        event: HookEvent,
        tool_name: str,
    ) -> list[Callable]:
        """Get hooks matching the event and tool name."""
        hooks_for_event = self._hooks.get(event, {})
        matching = []

        # Global hooks always match
        matching.extend(hooks_for_event.get("global", []))

        # Tool-specific hooks
        matching.extend(hooks_for_event.get(tool_name, []))

        # Wildcard hooks
        for pattern, hook_list in hooks_for_event.items():
            if pattern not in ("global", tool_name) and self._pattern_matches(pattern, tool_name):
                matching.extend(hook_list)

        return matching

    @staticmethod
    def _pattern_matches(pattern: str, tool_name: str) -> bool:
        """Check if a pattern matches a tool name."""
        if "*" in pattern:
            import fnmatch
            return fnmatch.fnmatch(tool_name, pattern)
        return pattern == tool_name


# Global instance
_claude_hook_manager: ClaudeStyleHookManager | None = None


def get_claude_hook_manager() -> ClaudeStyleHookManager:
    """Get or create the global Claude-style hook manager."""
    global _claude_hook_manager
    if _claude_hook_manager is None:
        _claude_hook_manager = ClaudeStyleHookManager()
    return _claude_hook_manager