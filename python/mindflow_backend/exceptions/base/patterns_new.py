"""Exception patterns and templates for MindFlow.

Provides builder patterns and exception templates following
best practices from examples while keeping simplicity.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .core_new import MindFlowError


class ExceptionBuilder:
    """Builder pattern for constructing exceptions with fluent interface."""
    
    def __init__(self, message: str, exception_class: Type[MindFlowError]):
        self.message = message
        self.exception_class = exception_class
        self._params = {}
    
    def with_param(self, key: str, value: Any) -> ExceptionBuilder:
        """Add a parameter to the exception."""
        self._params[key] = value
        return self
    
    def with_context(self, **context: Any) -> ExceptionBuilder:
        """Add context information."""
        self._params.update(context)
        return self
    
    def build(self) -> MindFlowError:
        """Build the final exception."""
        return self.exception_class(self.message, **self._params)


class ValidationErrorBuilder(ExceptionBuilder):
    """Builder for validation errors with field-specific context."""
    
    def __init__(self, message: str):
        super().__init__(message, ValidationError)
    
    def for_field(self, field: str) -> ValidationErrorBuilder:
        """Set the field that failed validation."""
        return self.with_param("field", field)
    
    def with_value(self, value: Any) -> ValidationErrorBuilder:
        """Set the invalid value."""
        return self.with_param("value", value)
    
    def expecting_format(self, format_type: str) -> ValidationErrorBuilder:
        """Set the expected format."""
        return self.with_param("expected_format", format_type)
    
    def with_user_message(self, message: str) -> ValidationErrorBuilder:
        """Set user-friendly message."""
        return self.with_param("user_message", message)
    
    def with_suggestion(self, suggestion: str) -> ValidationErrorBuilder:
        """Set helpful suggestion."""
        return self.with_param("suggestion", suggestion)
    
    def build(self) -> ValidationError:
        """Build the final ValidationError."""
        return self.exception_class(self.message, **self._params)


class AuthenticationErrorBuilder(ExceptionBuilder):
    """Builder for authentication errors."""
    
    def __init__(self, message: str):
        super().__init__(message, AuthenticationError)
    
    def with_auth_method(self, method: str) -> AuthenticationErrorBuilder:
        """Set authentication method."""
        return self.with_param("auth_method", method)
    
    def for_user(self, user_identifier: str) -> AuthenticationErrorBuilder:
        """Set user identifier."""
        return self.with_param("user_identifier", user_identifier)
    
    def from_provider(self, provider: str) -> AuthenticationErrorBuilder:
        """Set authentication provider."""
        return self.with_param("auth_provider", provider)
    
    def with_failure_reason(self, reason: str) -> AuthenticationErrorBuilder:
        """Set failure reason."""
        return self.with_param("failure_reason", reason)
    
    def with_error_code(self, code: str) -> AuthenticationErrorBuilder:
        """Set error code."""
        return self.with_param("error_code", code)
    
    def with_suggestion(self, suggestion: str) -> AuthenticationErrorBuilder:
        """Set helpful suggestion."""
        return self.with_param("suggestion", suggestion)
    
    def build(self) -> AuthenticationError:
        """Build the final AuthenticationError."""
        return self.exception_class(self.message, **self._params)


class NetworkErrorBuilder(ExceptionBuilder):
    """Builder for network errors."""
    
    def __init__(self, message: str):
        super().__init__(message, NetworkError)
    
    def for_endpoint(self, endpoint: str) -> NetworkErrorBuilder:
        """Set target endpoint."""
        return self.with_param("endpoint", endpoint)
    
    def with_timeout(self, timeout: float) -> NetworkErrorBuilder:
        """Set timeout duration."""
        return self.with_param("timeout", timeout)
    
    def with_retry_count(self, count: int) -> NetworkErrorBuilder:
        """Set retry count."""
        return self.with_param("retry_count", count)
    
    def for_component(self, component: str) -> NetworkErrorBuilder:
        """Set component name."""
        return self.with_param("component", component)
    
    def build(self) -> NetworkError:
        """Build the final NetworkError."""
        return self.exception_class(self.message, **self._params)


class ExceptionTemplates:
    """Templates for common error patterns following examples."""
    
    @staticmethod
    def missing_required_field(field: str, value: Any = None) -> ExceptionBuilder:
        """Template for missing required field."""
        return ValidationErrorBuilder(f"Missing required field: {field}")
            .for_field(field)
            .with_value(value)
            .with_user_message(f"The '{field}' field is required")
            .with_suggestion(f"Please provide a valid {field}")
    
    @staticmethod
    def invalid_format(field: str, value: Any, expected_format: str) -> ExceptionBuilder:
        """Template for invalid format."""
        return ValidationErrorBuilder(f"Invalid {field} format")
            .for_field(field)
            .with_value(value)
            .expecting_format(expected_format)
            .with_user_message(f"The '{field}' must be in {expected_format} format")
            .with_suggestion(f"Please provide {field} in correct format")
    
    @staticmethod
    def authentication_failed(reason: str, user_identifier: str = None) -> ExceptionBuilder:
        """Template for authentication failure."""
        return AuthenticationErrorBuilder(f"Authentication failed: {reason}")
            .for_user(user_identifier)
            .with_failure_reason(reason)
            .with_user_message("Authentication failed")
            .with_suggestion("Please check your credentials and try again")
    
    @staticmethod
    def network_timeout(endpoint: str, timeout: float) -> ExceptionBuilder:
        """Template for network timeout."""
        return NetworkErrorBuilder(f"Network timeout for {endpoint}")
            .for_endpoint(endpoint)
            .with_timeout(timeout)
            .with_user_message(f"Request to {endpoint} timed out")
            .with_suggestion("Please check your connection and try again")
    
    @staticmethod
    def resource_exhausted(resource: str, current_usage: str = None) -> ExceptionBuilder:
        """Template for resource exhaustion."""
        return ExceptionBuilder(f"Resource {resource} exhausted")
            .with_param("resource_type", resource)
            .with_param("current_usage", current_usage)
            .with_user_message(f"The {resource} is currently unavailable")
            .with_suggestion("Please try again later")


# Import exception classes for builders
if TYPE_CHECKING:
    from .core_new import ValidationError, AuthenticationError, NetworkError, ResourceError, SystemError
