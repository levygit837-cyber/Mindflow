"""Error recovery and resilience for LightPanda browsers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from mindflow_backend.infra.error_handling.retry_manager import (
    RetryConfig,
    with_granular_retry,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ErrorType(str, Enum):
    """Types of browser errors."""
    CONNECTION_FAILED = "connection_failed"
    NAVIGATION_FAILED = "navigation_failed"
    TIMEOUT = "timeout"
    CRASH = "crash"
    DEADLOCK = "deadlock"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"


@dataclass
class RecoveryStrategy:
    """Recovery strategy for specific error type."""
    error_type: ErrorType
    max_retries: int
    backoff_base: float
    backoff_max: float
    fallback_action: str  # "retry", "new_browser", "abort"
    destroy_browser: bool


class BrowserResilienceManager:
    """Manages recovery of browser errors."""

    def __init__(self):
        """Initialize the resilience manager."""
        self._logger = get_logger(__name__)

        # Recovery strategies by error type
        self._strategies: dict[ErrorType, RecoveryStrategy] = {
            ErrorType.CONNECTION_FAILED: RecoveryStrategy(
                error_type=ErrorType.CONNECTION_FAILED,
                max_retries=3,
                backoff_base=1.0,
                backoff_max=30.0,
                fallback_action="new_browser",
                destroy_browser=False,
            ),
            ErrorType.NAVIGATION_FAILED: RecoveryStrategy(
                error_type=ErrorType.NAVIGATION_FAILED,
                max_retries=5,
                backoff_base=0.5,
                backoff_max=10.0,
                fallback_action="retry",
                destroy_browser=False,
            ),
            ErrorType.TIMEOUT: RecoveryStrategy(
                error_type=ErrorType.TIMEOUT,
                max_retries=3,
                backoff_base=2.0,
                backoff_max=60.0,
                fallback_action="new_browser",
                destroy_browser=False,
            ),
            ErrorType.CRASH: RecoveryStrategy(
                error_type=ErrorType.CRASH,
                max_retries=1,
                backoff_base=0.0,
                backoff_max=0.0,
                fallback_action="new_browser",
                destroy_browser=True,
            ),
            ErrorType.DEADLOCK: RecoveryStrategy(
                error_type=ErrorType.DEADLOCK,
                max_retries=1,
                backoff_base=0.0,
                backoff_max=0.0,
                fallback_action="new_browser",
                destroy_browser=True,
            ),
            ErrorType.RESOURCE_EXHAUSTED: RecoveryStrategy(
                error_type=ErrorType.RESOURCE_EXHAUSTED,
                max_retries=2,
                backoff_base=5.0,
                backoff_max=120.0,
                fallback_action="new_browser",
                destroy_browser=False,
            ),
        }

        # Deadlock detection
        self._operation_start_times: dict[str, datetime] = {}
        self._deadlock_threshold = timedelta(seconds=30)

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error into specific type.

        Args:
            error: Exception to classify

        Returns:
            ErrorType: Classified error type
        """
        error_str = str(error).lower()

        if "connection" in error_str or "cdp" in error_str:
            return ErrorType.CONNECTION_FAILED
        elif "navigation" in error_str or "goto" in error_str:
            return ErrorType.NAVIGATION_FAILED
        elif "timeout" in error_str:
            return ErrorType.TIMEOUT
        elif "crash" in error_str or "killed" in error_str or "exited" in error_str:
            return ErrorType.CRASH
        elif "deadlock" in error_str:
            return ErrorType.DEADLOCK
        elif "memory" in error_str or "resource" in error_str:
            return ErrorType.RESOURCE_EXHAUSTED
        else:
            return ErrorType.UNKNOWN

    async def execute_with_resilience(
        self,
        operation: Callable,
        operation_id: str,
        error_context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute operation with resilient recovery.

        Args:
            operation: Operation to execute
            operation_id: Unique operation ID for tracking
            error_context: Additional error context

        Returns:
            Any: Operation result

        Raises:
            RuntimeError: If all retries fail
        """
        error_context = error_context or {}
        last_error = None
        strategy = None

        for attempt in range(10):  # Max 10 attempts total
            try:
                # Track operation start time for deadlock detection
                self._operation_start_times[operation_id] = datetime.utcnow()

                # Execute operation
                result = await operation()

                # Clear deadlock tracking
                if operation_id in self._operation_start_times:
                    del self._operation_start_times[operation_id]

                return result

            except Exception as error:
                last_error = error
                error_type = self.classify_error(error)
                strategy = self._strategies.get(
                    error_type, self._strategies[ErrorType.UNKNOWN]
                )

                self._logger.warning(
                    "operation_failed",
                    operation_id=operation_id,
                    attempt=attempt + 1,
                    error_type=error_type.value,
                    error=str(error),
                )

                # Check if should retry
                if attempt >= strategy.max_retries:
                    self._logger.error(
                        "max_retries_exceeded",
                        operation_id=operation_id,
                        max_retries=strategy.max_retries,
                    )
                    break

                # Apply backoff
                backoff = min(
                    strategy.backoff_base * (2 ** attempt), strategy.backoff_max
                )
                await asyncio.sleep(backoff)

        # All retries failed
        raise RuntimeError(
            f"Operation {operation_id} failed after all retries: {last_error}"
        ) from last_error

    async def check_deadlocks(self) -> list[str]:
        """Detect operations in deadlock.

        Returns:
            list[str]: List of deadlocked operation IDs
        """
        now = datetime.utcnow()
        deadlocked = []

        for operation_id, start_time in list(self._operation_start_times.items()):
            if now - start_time > self._deadlock_threshold:
                deadlocked.append(operation_id)
                self._logger.error(
                    "deadlock_detected",
                    operation_id=operation_id,
                    duration_seconds=(now - start_time).total_seconds(),
                )

        return deadlocked

    async def clear_deadlock(self, operation_id: str) -> bool:
        """Clear deadlock tracking for operation.

        Args:
            operation_id: Operation ID

        Returns:
            bool: True if tracking was cleared
        """
        if operation_id in self._operation_start_times:
            del self._operation_start_times[operation_id]
            return True
        return False
