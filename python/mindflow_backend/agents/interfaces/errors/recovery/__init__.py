"""Error recovery interfaces.

Provides contracts for error recovery strategies including retry mechanisms,
circuit breakers, fallback handlers, and automated recovery processes.
"""

from .error_recovery import ErrorRecoveryContract
from .retry_strategy import RetryStrategyContract
from .circuit_breaker import CircuitBreakerContract
from .fallback_handler import FallbackHandlerContract

__all__ = [
    "ErrorRecoveryContract",
    "RetryStrategyContract", 
    "CircuitBreakerContract",
    "FallbackHandlerContract",
]
