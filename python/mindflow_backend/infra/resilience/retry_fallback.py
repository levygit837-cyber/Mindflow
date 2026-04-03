"""Retry with fallback mechanism inspired by Claude Code.

Provides with_retry_and_fallback() decorator with exponential backoff + jitter
and automatic fallback to alternative operations.
"""

from __future__ import annotations

import asyncio
import functools
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from mindflow_backend.infra.error_handling.classifier import (
    ErrorCategory,
    classify_error,
    is_retryable,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class RetryFallbackConfig:
    """Configuration for retry with fallback behavior.

    Inspired by Claude Code's withRetry implementation.
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True
    exponential_base: float = 2.0

    # Fallback settings
    fallback_enabled: bool = True
    fallback_on_categories: set[ErrorCategory] = field(
        default_factory=lambda: {
            ErrorCategory.CAPACITY,
            ErrorCategory.SERVER_OVERLOAD,
            ErrorCategory.CIRCUIT_OPEN,
        }
    )

    # Retry settings
    retry_on_categories: set[ErrorCategory] = field(
        default_factory=lambda: {
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.SERVER_OVERLOAD,
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.CAPACITY,
            ErrorCategory.AUTH_TRANSIENT,
        }
    )


@dataclass
class RetryContext:
    """Context for retry operations.

    Tracks retry state and provides information for retry decisions.
    """

    attempt: int = 0
    max_retries: int = 3
    last_error: Exception | None = None
    last_error_category: ErrorCategory | None = None
    total_elapsed: float = 0.0
    start_time: float = field(default_factory=time.monotonic)

    def should_retry(self) -> bool:
        """Check if should retry based on attempt count."""
        return self.attempt < self.max_retries

    def get_next_delay(self, config: RetryFallbackConfig) -> float:
        """Calculate next retry delay with exponential backoff + jitter."""
        delay = min(
            config.base_delay * (config.exponential_base ** self.attempt),
            config.max_delay,
        )
        if config.jitter:
            delay *= 0.5 + random.random()
        return delay


class RetryFallbackError(Exception):
    """Error raised when retry and fallback both fail."""

    def __init__(
        self,
        message: str,
        *,
        retry_context: RetryContext | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.retry_context = retry_context
        self.original_error = original_error


def with_retry_and_fallback(
    config: RetryFallbackConfig | None = None,
    fallback: Callable[..., Any] | None = None,
) -> Callable:
    """Decorator for retry with fallback functionality.

    Provides exponential backoff + jitter retry with automatic fallback
    to alternative operations for capacity/overload errors.

    Args:
        config: Retry configuration
        fallback: Fallback function to call when all retries fail

    Returns:
        Decorator function

    Example:
        @with_retry_and_fallback(
            config=RetryFallbackConfig(max_retries=3),
            fallback=lambda: {"status": "degraded"}
        )
        async def call_api():
            return await api_client.request()
    """
    cfg = config or RetryFallbackConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            context = RetryContext(max_retries=cfg.max_retries)
            last_exception: Exception | None = None

            while context.should_retry():
                try:
                    result = await func(*args, **kwargs)
                    if context.attempt > 0:
                        _logger.info(
                            "retry_succeeded",
                            function=func.__name__,
                            attempt=context.attempt,
                        )
                    return result

                except Exception as exc:
                    last_exception = exc
                    context.last_error = exc
                    context.last_error_category = classify_error(exc)
                    context.attempt += 1
                    context.total_elapsed = time.monotonic() - context.start_time

                    # Check if should retry
                    if not is_retryable(exc):
                        _logger.warning(
                            "retry_not_retryable",
                            function=func.__name__,
                            error_type=type(exc).__name__,
                        )
                        break

                    if not context.should_retry():
                        _logger.warning(
                            "retry_max_retries_exceeded",
                            function=func.__name__,
                            max_retries=cfg.max_retries,
                        )
                        break

                    # Calculate delay
                    delay = context.get_next_delay(cfg)
                    _logger.info(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=context.attempt,
                        delay=delay,
                        error_type=type(exc).__name__,
                    )

                    await asyncio.sleep(delay)

            # All retries exhausted
            # Try fallback if enabled and error category matches
            if (
                cfg.fallback_enabled
                and fallback is not None
                and context.last_error_category in cfg.fallback_on_categories
            ):
                _logger.warning(
                    "retry_fallback_triggered",
                    function=func.__name__,
                    error_category=context.last_error_category.value,
                )
                try:
                    return await fallback(*args, **kwargs)
                except Exception as fallback_exc:
                    _logger.error(
                        "retry_fallback_failed",
                        function=func.__name__,
                        error=str(fallback_exc),
                    )

            # No fallback or fallback failed
            raise RetryFallbackError(
                f"All {cfg.max_retries} retries failed for {func.__name__}",
                retry_context=context,
                original_error=last_exception,
            )

        return wrapper

    return decorator


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    delay = min(
        base_delay * (exponential_base ** attempt),
        max_delay,
    )
    if jitter:
        delay *= 0.5 + random.random()
    return delay