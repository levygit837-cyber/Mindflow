"""Resilience utilities — retry, circuit breaker, and timeout configs.

Consolidated module that re-exports:
- Retry logic (tenacity-based)
- Unified circuit breaker from circuit_breaker subpackage
- Backward-compatible aliases for legacy imports
"""

from __future__ import annotations

from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from mindflow_backend.infra.logging import get_logger

# Re-export unified circuit breaker
from .circuit_breaker import (
    AdaptiveThresholdType,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerMetrics,
    CircuitBreakerStats,
    CircuitOpenError,
    CircuitState,
    EnhancedCircuitBreaker,
    EnhancedCircuitBreakerConfig,
    circuit_protected,
    get_all_breakers,
    get_all_stats,
    get_breaker,
    reset_all_breakers,
)

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------


class RetryConfig(BaseModel):
    """Configuration for retry behaviour."""

    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 30.0
    jitter: bool = True
    retry_on_status: list[int] = [429, 500, 502, 503, 504]


def with_retry(config: RetryConfig | None = None):
    """Create a tenacity retry decorator from a RetryConfig."""
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


__all__ = [
    # Retry
    "RetryConfig",
    "with_retry",
    # Circuit Breaker (unified)
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
    # Enhanced
    "AdaptiveThresholdType",
    "EnhancedCircuitBreaker",
    "EnhancedCircuitBreakerConfig",
    # Metrics
    "CircuitBreakerMetrics",
]