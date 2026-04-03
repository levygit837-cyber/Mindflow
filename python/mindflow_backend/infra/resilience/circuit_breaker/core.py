"""Core circuit breaker implementation.

Consolidated from communication/circuit_breaker, grpc/resilience,
and infra/resilience into a single, reusable base implementation.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is in the OPEN state."""


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0
    max_half_open_calls: int = 3
    fallback_enabled: bool = True


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """Unified circuit breaker for fault tolerance.

    Consolidates implementations from:
    - communication/circuit_breaker/breaker.py
    - grpc/resilience/circuit_breaker.py
    - infra/resilience.py

    States: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._last_opened_time: float | None = None
        self._half_open_calls = 0
        self._fallback_handler: Callable | None = None
        self._lock: asyncio.Lock | None = None

    @property
    def state(self) -> CircuitState:
        """Get current state, auto-transitioning OPEN to HALF_OPEN if timeout elapsed."""
        if self._state == CircuitState.OPEN and self._last_opened_time:
            elapsed = time.monotonic() - self._last_opened_time
            if elapsed >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self.stats.consecutive_successes = 0
                _logger.info(
                    "circuit_half_open",
                    name=self.name,
                    recovery_timeout=self.config.recovery_timeout,
                )
        return self._state

    def _get_lock(self) -> asyncio.Lock:
        """Lazy-init asyncio lock for thread safety."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def set_fallback_handler(self, handler: Callable) -> None:
        """Set a fallback handler for when circuit is open."""
        self._fallback_handler = handler

    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.OPEN:
            return False
        # HALF_OPEN: allow limited calls
        return self._half_open_calls < self.config.max_half_open_calls

    def record_success(self) -> None:
        """Record a successful request."""
        self.stats.total_requests += 1
        self.stats.successful_requests += 1
        self.stats.consecutive_successes += 1
        self.stats.consecutive_failures = 0
        self.stats.last_success_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self.stats.consecutive_successes >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._half_open_calls = 0
                _logger.info(
                    "circuit_closed",
                    name=self.name,
                    success_threshold=self.config.success_threshold,
                )
        elif self._state == CircuitState.CLOSED:
            self.stats.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self.stats.total_requests += 1
        self.stats.failed_requests += 1
        self.stats.consecutive_failures += 1
        self.stats.consecutive_successes = 0
        self.stats.last_failure_time = time.monotonic()

        if self._state == CircuitState.CLOSED:
            if self.stats.consecutive_failures >= self.config.failure_threshold:
                self._transition_to_open()
        elif self._state == CircuitState.HALF_OPEN:
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        self._state = CircuitState.OPEN
        self._last_opened_time = time.monotonic()
        self.stats.circuit_opened_count += 1
        _logger.warning(
            "circuit_opened",
            name=self.name,
            failures=self.stats.consecutive_failures,
            threshold=self.config.failure_threshold,
        )

    async def execute(self, func: Callable, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute a function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function positional arguments
            **kwargs: Function keyword arguments

        Returns:
            Execution result dict
        """
        if not self.can_execute():
            _logger.warning("circuit_blocked", name=self.name, state=self.state.value)
            if self.config.fallback_enabled and self._fallback_handler:
                return await self._fallback_handler(*args, **kwargs)
            return {
                "success": False,
                "error": f"Circuit {self.name} is {self.state.value}",
                "circuit_state": self.state.value,
            }

        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout,
            )
            if isinstance(result, dict) and result.get("success") is False:
                self.record_failure()
            else:
                self.record_success()
            return result
        except TimeoutError:
            self.record_failure()
            if self.config.fallback_enabled and self._fallback_handler:
                return await self._fallback_handler(*args, **kwargs)
            return {
                "success": False,
                "error": f"Circuit {self.name}: timeout after {self.config.timeout}s",
                "circuit_state": self.state.value,
            }
        except Exception as e:
            _logger.error("circuit_exception", name=self.name, error=str(e))
            self.record_failure()
            if self.config.fallback_enabled and self._fallback_handler:
                return await self._fallback_handler(*args, **kwargs)
            return {
                "success": False,
                "error": str(e),
                "circuit_state": self.state.value,
            }

    def check(self) -> None:
        """Check if a call is allowed (sync version).

        Raises:
            CircuitOpenError: If circuit is open
        """
        state = self.state
        if state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit '{self.name}' is OPEN. "
                f"Retry after {self.config.recovery_timeout}s."
            )
        if state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.max_half_open_calls:
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is HALF_OPEN and max test requests reached."
                )
            self._half_open_calls += 1

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        total = self.stats.total_requests
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": total,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "circuit_opened_count": self.stats.circuit_opened_count,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "failure_rate": (
                self.stats.failed_requests / total * 100 if total > 0 else 0.0
            ),
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._last_opened_time = None
        self._half_open_calls = 0
        _logger.info("circuit_reset", name=self.name)

    def force_open(self) -> None:
        """Force circuit to OPEN state (for testing)."""
        self._transition_to_open()

    def force_close(self) -> None:
        """Force circuit to CLOSED state (for testing)."""
        self._state = CircuitState.CLOSED
        self.stats.consecutive_failures = 0
        self._half_open_calls = 0