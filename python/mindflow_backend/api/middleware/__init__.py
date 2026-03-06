"""API middleware for MindFlow.

Provides error handling, logging, and other cross-cutting concerns
for FastAPI applications.
"""

from .error_handler import ErrorHandlerMiddleware

__all__ = ["ErrorHandlerMiddleware"]
