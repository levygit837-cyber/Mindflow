"""Error handling utilities for MindFlow backend.

Provides helper functions, decorators, and utilities for consistent
error handling across the system.
"""

from .error_handling import (
    CircuitBreaker,
    ErrorContext,
    create_error_context,
    handle_errors,
    retry_on_error,
    timeout_handler,
)
from .error_setup import (
    create_error_handling_config,
    setup_comprehensive_error_handling,
    setup_fastapi_error_handling,
    setup_grpc_error_handling,
)

__all__ = [
    # Error handling utilities
    "handle_errors",
    "retry_on_error", 
    "timeout_handler",
    "ErrorContext",
    "CircuitBreaker",
    "create_error_context",
    
    # Error setup utilities
    "setup_fastapi_error_handling",
    "setup_grpc_error_handling",
    "setup_comprehensive_error_handling",
    "create_error_handling_config",
]
