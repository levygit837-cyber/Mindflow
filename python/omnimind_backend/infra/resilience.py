"""Resilience utilities — retry, circuit breaker, and timeout configs.

Uses ``tenacity`` for retry logic with exponential backoff and jitter.
Includes a lightweight circuit breaker implementation.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------------


class RetryConfig(BaseModel):
    """Configuration for retry behaviour."""

    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 30.0
    jitter: bool = True
    retry_on_status: list[int] = [429, 500, 502, 503, 504]


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max: int = 1


# ---------------------------------------------------------------------------
# Retry decorator factory
# ---------------------------------------------------------------------------


def with_retry(config: RetryConfig | None = None):
    """Create a tenacity retry decorator from a ``RetryConfig``.

    Usage::

        @with_retry()
        async def my_function(): ...
    """
    cfg = config or RetryConfig()
    return retry(
        stop=stop_after_attempt(cfg.max_retries + 1),
        wait=wait_exponential_jitter(
            initial=cfg.backoff_base,
            max=cfg.backoff_max,
            jitter=cfg.backoff_base if cfg.jitter else 0,
        ),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is in the OPEN state."""


@dataclass
class CircuitBreaker:
    """Lightweight per-provider circuit breaker.

    States: CLOSED → OPEN → HALF_OPEN → CLOSED
    """

    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _state: str = "CLOSED"
    _failures: deque = field(default_factory=deque)
    _last_failure_time: float = 0.0
    _half_open_attempts: int = 0

    @property
    def state(self) -> str:
        if self._state == "OPEN":
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self._state = "HALF_OPEN"
                self._half_open_attempts = 0
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == "HALF_OPEN":
            self._state = "CLOSED"
            self._failures.clear()
        elif self._state == "CLOSED":
            # Remove old failures outside the window.
            self._failures.clear()

    def record_failure(self) -> None:
        """Record a failed call."""
        now = time.monotonic()
        self._last_failure_time = now
        self._failures.append(now)

        if self._state == "HALF_OPEN":
            self._state = "OPEN"
            _logger.warning("circuit_breaker_opened", reason="half_open_failure")
            return

        if len(self._failures) >= self.config.failure_threshold:
            self._state = "OPEN"
            _logger.warning(
                "circuit_breaker_opened",
                failures=len(self._failures),
                threshold=self.config.failure_threshold,
            )

    def check(self) -> None:
        """Check if a call is allowed.

        Raises:
            CircuitOpenError: If the circuit is open and recovery timeout
                has not elapsed.
        """
        state = self.state  # triggers OPEN → HALF_OPEN transition
        if state == "OPEN":
            raise CircuitOpenError(
                f"Circuit is OPEN. Retry after {self.config.recovery_timeout}s."
            )
        if state == "HALF_OPEN" and self._half_open_attempts >= self.config.half_open_max:
            raise CircuitOpenError("Circuit is HALF_OPEN and max test requests reached.")
        if state == "HALF_OPEN":
            self._half_open_attempts += 1
