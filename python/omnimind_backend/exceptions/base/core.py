"""Core base exceptions for OmniMind.

Root exceptions that all other system exceptions inherit from.
Provides structured error handling with context and metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional


class OmniMindError(Exception):
    """Base exception for all OmniMind system errors.
    
    Provides structured error information including:
    - Unique error ID for tracking
    - Error context metadata
    - Timestamp for debugging
    - Component identification
    """
    
    def __init__(
        self,
        message: str,
        *,
        error_id: Optional[str] = None,
        component: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.error_id = error_id or str(uuid.uuid4())
        self.component = component
        self.session_id = session_id
        self.user_id = user_id
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.cause = cause
        
    def __str__(self) -> str:
        return f"[{self.error_id}] {super().__str__()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "message": str(self),
            "component": self.component,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }


class SystemError(OmniMindError):
    """Base exception for system-level errors.
    
    Used for infrastructure, configuration, and operational errors
    that are not related to business logic.
    """
    
    def __init__(
        self,
        message: str,
        *,
        severity: str = "high",
        recoverable: bool = False,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.severity = severity
        self.recoverable = recoverable


class ConfigurationError(SystemError):
    """Raised when system configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        *,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", recoverable=True, **kwargs)
        self.config_key = config_key
        self.expected_type = expected_type


class InfrastructureError(SystemError):
    """Raised when infrastructure components fail (DB, Redis, etc.)."""
    
    def __init__(
        self,
        message: str,
        *,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="high", recoverable=True, **kwargs)
        self.service = service
        self.operation = operation


class NetworkError(SystemError):
    """Raised when network operations fail."""
    
    def __init__(
        self,
        message: str,
        *,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", recoverable=True, **kwargs)
        self.endpoint = endpoint
        self.timeout = timeout


class ResourceError(SystemError):
    """Raised when system resources are exhausted or unavailable."""
    
    def __init__(
        self,
        message: str,
        *,
        resource_type: Optional[str] = None,
        current_usage: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="high", recoverable=False, **kwargs)
        self.resource_type = resource_type
        self.current_usage = current_usage


class TimeoutError(SystemError):
    """Raised when operations exceed their time limits."""
    
    def __init__(
        self,
        message: str,
        *,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", recoverable=True, **kwargs)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
