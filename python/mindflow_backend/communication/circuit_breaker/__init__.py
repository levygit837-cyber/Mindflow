"""Circuit breaker for MindFlow agent communication.

DEPRECATED: This module re-exports from infra.resilience.circuit_breaker.
Import directly from mindflow_backend.infra.resilience.circuit_breaker instead.
"""

from mindflow_backend.infra.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitOpenError,
    CircuitState,
    circuit_protected,
    get_all_breakers,
    get_all_stats,
    get_breaker,
    reset_all_breakers,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitOpenError",
    "CircuitState",
    "circuit_protected",
    "get_breaker",
    "get_all_breakers",
    "get_all_stats",
    "reset_all_breakers",
]
