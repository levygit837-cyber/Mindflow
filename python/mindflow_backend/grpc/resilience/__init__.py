"""gRPC resilience patterns and fault tolerance.

Provides circuit breaker, retry policies, timeout management, and other
resilience patterns for gRPC services to handle failures gracefully.
"""

from .circuit_breaker import GrpcCircuitBreaker
from .retry import AdvancedRetryPolicy, RetryableError
from .timeout import TimeoutManager
from .bulkhead import GrpcBulkhead
from .fallback import FallbackStrategy, FallbackManager
from .enhanced_circuit_breaker import (
    AdaptiveThresholdType, EnhancedGrpcCircuitBreaker, EnhancedCircuitBreakerConfig
)
from .advanced_retry import AdvancedRetryPolicy as EnhancedAdvancedRetryPolicy

__all__ = [
    "GrpcCircuitBreaker",
    "AdvancedRetryPolicy",
    "RetryableError",
    "TimeoutManager",
    "GrpcBulkhead",
    "FallbackStrategy",
    "FallbackManager",
    "AdaptiveThresholdType",
    "EnhancedGrpcCircuitBreaker",
    "EnhancedCircuitBreakerConfig",
    "EnhancedAdvancedRetryPolicy",
]
