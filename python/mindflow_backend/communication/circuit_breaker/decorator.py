"""DEPRECATED: Re-exports from infra.resilience.circuit_breaker.decorator."""

from mindflow_backend.infra.resilience.circuit_breaker.decorator import (
    circuit_protected,
    get_all_breakers,
    get_all_stats,
    get_breaker,
    reset_all_breakers,
)

__all__ = [
    "circuit_protected",
    "get_breaker",
    "get_all_breakers",
    "get_all_stats",
    "reset_all_breakers",
]
