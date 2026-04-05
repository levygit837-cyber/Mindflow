"""Timeout manager for centralized timeout enforcement.

Provides timeout enforcement with asyncio support and graceful shutdown.

TODO: Integrate with CLI
- CLI should enforce same timeout policies as backend
- CLI should use same timeout hierarchy (global < operation < specific)

TODO: Integrate with Desktop
- Desktop should enforce same timeout policies as backend
- Desktop should use same timeout hierarchy (global < operation < specific)
"""

from __future__ import annotations

import asyncio
import signal
import sys
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from mindflow_backend.infra.logging import get_logger

from .config import (
    DEFAULT_BASH_TIMEOUT_MS,
    DEFAULT_HTTP_HOOK_TIMEOUT_MS,
    DEFAULT_LSP_TIMEOUT_MS,
    SESSION_END_HOOK_TIMEOUT_MS,
    TOOL_HOOK_EXECUTION_TIMEOUT_MS,
)

# Python 3.11+ has asyncio.timeout, use wait_for for older versions
if sys.version_info >= (3, 11):
    _has_timeout = True
else:
    _has_timeout = False

_logger = get_logger(__name__)


@dataclass
class TimeoutResult:
    """Result of a timeout-protected operation."""

    completed: bool
    timed_out: bool
    duration_ms: float
    error: str | None = None


class TimeoutManager:
    """Centralized timeout management.

    Features:
    - Asyncio-based timeout enforcement
    - Graceful shutdown with SIGTERM
    - Timeout hierarchy (global < operation < specific)
    - Logging of timeout events
    """

    def __init__(self):
        """Initialize timeout manager."""
        self._timeouts: dict[str, int] = {
            "bash": DEFAULT_BASH_TIMEOUT_MS,
            "http_hook": DEFAULT_HTTP_HOOK_TIMEOUT_MS,
            "tool_hook": TOOL_HOOK_EXECUTION_TIMEOUT_MS,
            "session_end_hook": SESSION_END_HOOK_TIMEOUT_MS,
            "lsp": DEFAULT_LSP_TIMEOUT_MS,
        }

    def set_timeout(self, operation: str, timeout_ms: int) -> None:
        """Set timeout for a specific operation.

        Args:
            operation: Operation name (e.g., "bash", "http_hook")
            timeout_ms: Timeout in milliseconds
        """
        self._timeouts[operation] = timeout_ms
        _logger.debug("timeout_set", operation=operation, timeout_ms=timeout_ms)

    def get_timeout(self, operation: str, default_ms: int | None = None) -> int:
        """Get timeout for a specific operation.

        Args:
            operation: Operation name
            default_ms: Default timeout if not configured

        Returns:
            Timeout in milliseconds
        """
        return self._timeouts.get(operation, default_ms or 60_000)

    @asynccontextmanager
    async def timeout_context(
        self, operation: str, timeout_ms: int | None = None
    ) -> Any:
        """Context manager for timeout enforcement.

        Args:
            operation: Operation name
            timeout_ms: Custom timeout in milliseconds (overrides default)

        Yields:
            None

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        actual_timeout = timeout_ms or self.get_timeout(operation)
        timeout_seconds = actual_timeout / 1000.0

        _logger.debug("timeout_context_entered", operation=operation, timeout_ms=actual_timeout)

        try:
            if _has_timeout:
                async with asyncio.timeout(timeout_seconds):
                    yield
            else:
                # For Python < 3.11, we can't use asyncio.timeout
                # Use a task-based approach with cancellation
                task = asyncio.current_task()
                if task is None:
                    # If not in a task context, just yield (no timeout enforcement)
                    yield
                else:
                    # Create a timeout task
                    async def timeout_handler():
                        await asyncio.sleep(timeout_seconds)
                        if not task.done():
                            task.cancel()

                    timeout_task = asyncio.create_task(timeout_handler())
                    try:
                        yield
                    finally:
                        timeout_task.cancel()
                        try:
                            await timeout_task
                        except asyncio.CancelledError:
                            pass
        except asyncio.CancelledError:
            # Check if it was due to timeout
            if not _has_timeout:
                _logger.warning(
                    "operation_timeout",
                    operation=operation,
                    timeout_ms=actual_timeout,
                )
                raise asyncio.TimeoutError(f"Operation '{operation}' timed out after {actual_timeout}ms")
            raise
        except TimeoutError:
            _logger.warning(
                "operation_timeout",
                operation=operation,
                timeout_ms=actual_timeout,
            )
            raise asyncio.TimeoutError(f"Operation '{operation}' timed out after {actual_timeout}ms")

    async def run_with_timeout(
        self,
        operation: str,
        coro,
        timeout_ms: int | None = None,
    ) -> TimeoutResult:
        """Run a coroutine with timeout enforcement.

        Args:
            operation: Operation name
            coro: Coroutine to run
            timeout_ms: Custom timeout in milliseconds (overrides default)

        Returns:
            TimeoutResult with completion status
        """
        start_time = datetime.now(UTC)
        actual_timeout = timeout_ms or self.get_timeout(operation)
        timeout_seconds = actual_timeout / 1000.0

        try:
            if _has_timeout:
                async with asyncio.timeout(timeout_seconds):
                    await coro
            else:
                await asyncio.wait_for(coro, timeout=timeout_seconds)

            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return TimeoutResult(
                completed=True,
                timed_out=False,
                duration_ms=duration_ms,
            )
        except TimeoutError:
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return TimeoutResult(
                completed=False,
                timed_out=True,
                duration_ms=duration_ms,
                error=f"Operation timed out after {actual_timeout}ms",
            )
        except Exception as e:
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return TimeoutResult(
                completed=False,
                timed_out=False,
                duration_ms=duration_ms,
                error=str(e),
            )

    async def run_with_graceful_shutdown(
        self,
        operation: str,
        coro,
        timeout_ms: int | None = None,
        grace_period_ms: int = 5_000,
    ) -> TimeoutResult:
        """Run a coroutine with timeout and graceful shutdown.

        Args:
            operation: Operation name
            coro: Coroutine to run
            timeout_ms: Custom timeout in milliseconds (overrides default)
            grace_period_ms: Grace period in milliseconds before force kill

        Returns:
            TimeoutResult with completion status
        """
        start_time = datetime.now(UTC)
        actual_timeout = timeout_ms or self.get_timeout(operation)
        timeout_seconds = actual_timeout / 1000.0
        grace_seconds = grace_period_ms / 1000.0

        task = asyncio.create_task(coro)

        try:
            # Wait with timeout
            await asyncio.wait_for(task, timeout=timeout_seconds)

            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return TimeoutResult(
                completed=True,
                timed_out=False,
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            # Grace period: try to cancel gracefully
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=grace_seconds)
                duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

                return TimeoutResult(
                    completed=True,
                    timed_out=False,
                    duration_ms=duration_ms,
                )
            except asyncio.TimeoutError:
                # Force cancel
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

                return TimeoutResult(
                    completed=False,
                    timed_out=True,
                    duration_ms=duration_ms,
                    error=f"Operation timed out after {actual_timeout}ms (grace period exhausted)",
                )
        except Exception as e:
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return TimeoutResult(
                completed=False,
                timed_out=False,
                duration_ms=duration_ms,
                error=str(e),
            )


# Global timeout manager instance
_timeout_manager: TimeoutManager | None = None


def get_timeout_manager() -> TimeoutManager:
    """Get global timeout manager instance.

    Returns:
        TimeoutManager instance
    """
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager
