"""Circuit breaker decorator.

Consolidated from communication/circuit_breaker/decorator.py
with unified circuit breaker registry.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

from .core import CircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)

_breaker_registry: dict[str, CircuitBreaker] = {}


def get_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    success_threshold: int = 3,
) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _breaker_registry:
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
        )
        _breaker_registry[name] = CircuitBreaker(name=name, config=config)
        logger.info("circuit_breaker_registered", name=name)
    return _breaker_registry[name]


def get_all_breakers() -> dict[str, CircuitBreaker]:
    """Get all registered circuit breakers."""
    return dict(_breaker_registry)


def get_all_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all registered circuit breakers."""
    return {name: cb.get_stats() for name, cb in _breaker_registry.items()}


def reset_all_breakers() -> None:
    """Reset all registered circuit breakers."""
    for cb in _breaker_registry.values():
        cb.reset()


def circuit_protected(
    breaker_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    success_threshold: int = 3,
    fallback_return: Any = None,
) -> Callable:
    """Decorator to protect async methods with circuit breaker.

    Args:
        breaker_name: Unique name for the circuit breaker
        failure_threshold: Failures before opening circuit
        recovery_timeout: Seconds before trying recovery
        success_threshold: Successes needed to close circuit
        fallback_return: Value to return when circuit is open

    Returns:
        Decorated function with circuit breaker protection
    """

    def decorator(func: Callable) -> Callable:
        breaker = get_breaker(
            name=breaker_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
        )

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not breaker.can_execute():
                logger.warning("circuit_open_fallback", name=breaker_name)
                return fallback_return

            try:
                result = await func(*args, **kwargs)
                if isinstance(result, dict) and result.get("success") is False:
                    breaker.record_failure()
                else:
                    breaker.record_success()
                return result
            except Exception as e:
                logger.error(
                    "circuit_exception",
                    name=breaker_name,
                    func=func.__name__,
                    error=str(e),
                )
                breaker.record_failure()
                return fallback_return

        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator