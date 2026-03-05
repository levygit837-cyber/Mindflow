"""gRPC interceptors for OmniMind.

Provides error handling, logging, and other cross-cutting concerns
for gRPC services.
"""

from .error_handler import ErrorHandlerInterceptor

__all__ = ["ErrorHandlerInterceptor"]
