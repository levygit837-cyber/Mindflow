"""Business logic exceptions for MindFlow.

Simplified business exceptions following examples pattern.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .core_new import MindFlowError


class BusinessLogicError(MindFlowError):
    """Base exception for business logic errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, component="business", **kwargs)


class ValidationError(BusinessLogicError):
    """Validation errors for user input and data."""
    
    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        value: Any = None,
        expected_format: Optional[str] = None,
        validation_rule: Optional[str] = None,
        user_message: Optional[str] = None,
        suggestion: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.expected_format = expected_format
        self.validation_rule = validation_rule
        self.user_message = user_message
        self.suggestion = suggestion


class AuthenticationError(BusinessLogicError):
    """Authentication and authorization errors."""
    
    def __init__(
        self,
        message: str,
        *,
        user_identifier: Optional[str] = None,
        auth_method: Optional[str] = None,
        auth_provider: Optional[str] = None,
        failure_reason: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.user_identifier = user_identifier
        self.auth_method = auth_method
        self.auth_provider = auth_provider
        self.failure_reason = failure_reason
        self.error_code = error_code


class AuthorizationError(AuthenticationError):
    """Authorization and permission errors."""
    
    def __init__(
        self,
        message: str,
        *,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required_permission = required_permission
        self.resource = resource


class NotFoundError(BusinessLogicError):
    """Resource not found errors."""
    
    def __init__(
        self,
        message: str,
        *,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id
