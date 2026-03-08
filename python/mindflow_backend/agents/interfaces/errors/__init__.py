"""Error handling interfaces.

Provides contracts for error handling, recovery strategies, and
error management across the MindFlow system. These interfaces
ensure consistent error handling patterns and type safety.
"""

from .base_error_handler import BaseErrorHandlerContract
from .storage_error_handler import StorageErrorHandlerContract
from .validation_error_handler import ValidationErrorHandlerContract
from .external_error_handler import ExternalErrorHandlerContract
from .infrastructure_error_handler import InfrastructureErrorHandlerContract
from .api_error_handler import APIErrorHandlerContract

from .recovery.error_recovery import ErrorRecoveryContract
from .recovery.retry_strategy import RetryStrategyContract
from .recovery.circuit_breaker import CircuitBreakerContract
from .recovery.fallback_handler import FallbackHandlerContract

__all__ = [
    # Base error handler interfaces
    "BaseErrorHandlerContract",
    "StorageErrorHandlerContract",
    "ValidationErrorHandlerContract",
    "ExternalErrorHandlerContract",
    "InfrastructureErrorHandlerContract",
    "APIErrorHandlerContract",
    
    # Recovery interfaces
    "ErrorRecoveryContract",
    "RetryStrategyContract",
    "CircuitBreakerContract",
    "FallbackHandlerContract",
]
