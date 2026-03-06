"""Base controller with security and utilities for all API controllers."""

from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.infra.middleware.auth import require_api_key
from omnimind_backend.infra.sanitizer import SanitizationError, sanitize_message
from omnimind_backend.storage.postgresql.connection import db_session

_logger = get_logger(__name__)
T = TypeVar("T")


class BaseController:
    """Base controller with common security, validation, and utilities."""
    
    def __init__(self):
        self.logger = _logger
        self.settings = get_settings()
    
    def get_db(self) -> Session:
        """Get database session dependency."""
        with db_session() as db:
            yield db
    
    def get_current_api_key(self, request: Request) -> str | None:
        """Get current API key from request."""
        return Depends(require_api_key)(request)
    
    def handle_error(self, error: Exception, context: str = "") -> HTTPException:
        """Standardized error handling."""
        self.logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        
        if isinstance(error, SanitizationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input validation error: {str(error)}"
            )
        elif isinstance(error, ValueError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input: {str(error)}"
            )
        else:
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize input text."""
        try:
            return sanitize_message(text)
        except SanitizationError as e:
            self.logger.warning(f"Sanitization failed: {str(e)}")
            raise
    
    def validate_session_id(self, session_id: str | None) -> str:
        """Validate and normalize session ID."""
        if not session_id:
            import uuid
            return f"sess-{uuid.uuid4()}"
        
        if len(session_id) < 3 or len(session_id) > 100:
            raise ValueError("Session ID must be between 3 and 100 characters")
        
        return session_id
    
    def log_request(self, request: Request, operation: str, **kwargs) -> None:
        """Log API request with context."""
        self.logger.info(
            f"API request: {operation}",
            path=request.url.path,
            method=request.method,
            **kwargs
        )


def require_auth(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to require authentication."""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        # The actual auth check is handled by FastAPI dependency injection
        # This decorator is mainly for documentation and future enhancements
        return await func(*args, **kwargs)
    return wrapper


def sanitize_input(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to sanitize string inputs."""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        # Sanitize any string parameters
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                try:
                    sanitized_kwargs[key] = sanitize_message(value)
                except SanitizationError:
                    raise
            else:
                sanitized_kwargs[key] = value
        
        return await func(*args, **sanitized_kwargs)
    return wrapper


def rate_limit(operation: str):
    """Decorator for rate limiting (placeholder for future implementation)."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # TODO: Implement actual rate limiting
            # For now, just log the operation
            _logger.debug(f"Rate limiting check for operation: {operation}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def audit_log(operation: str):
    """Decorator for audit logging."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = logging.time()
            try:
                result = await func(*args, **kwargs)
                duration = logging.time() - start_time
                _logger.info(
                    f"Audit: {operation} completed",
                    duration=duration,
                    success=True
                )
                return result
            except Exception as e:
                duration = logging.time() - start_time
                _logger.error(
                    f"Audit: {operation} failed",
                    duration=duration,
                    success=False,
                    error=str(e)
                )
                raise
        return wrapper
    return decorator
