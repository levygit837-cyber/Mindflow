"""Circuit breaker module.

Unified circuit breaker implementation consolidating:
- communication/circuit_breaker/
- grpc/resilience/circuit_breaker.py
- grpc/resilience/enhanced_circuit_breaker.py
- infra/resilience.py (circuit breaker portion)
"""

from .core import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitOpenError,
    CircuitState,
)
from .decorator import (
    circuit_protected,
    get_all_breakers,
    get_all_stats,
    get_breaker,
    reset_all_breakers,
)
from .enhanced import (
    AdaptiveThresholdType,
    EnhancedCircuitBreaker,
    EnhancedCircuitBreakerConfig,
)
from .metrics import CircuitBreakerMetrics

__all__ = [
    # Core
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitOpenError",
    "CircuitState",
    # Decorator
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