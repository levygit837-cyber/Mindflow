"""Enhanced exception patterns for MindFlow.

Provides builder patterns, fluent interfaces, and enhanced functionality
for creating and managing exceptions with better developer experience.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, Union, TYPE_CHECKING
from abc import ABC, abstractmethod
from contextlib import contextmanager
import uuid
from datetime import datetime

if TYPE_CHECKING:
    from .core import MindFlowError
    from .business import BusinessLogicError
    from ..schemas.errors import ErrorSchema


class ExceptionBuilder(ABC):
    """Abstract base class for exception builders."""
    
    @abstractmethod
    def build(self) -> Exception:
        """Build the exception instance."""
        ...


class MindFlowErrorBuilder(ExceptionBuilder):
    """Builder for MindFlowError exceptions with fluent interface."""
    
    def __init__(self, message: str, exception_class: Type[MindFlowError]):
        self._message = message
        self._exception_class = exception_class
        self._error_id = None
        self._component = None
        self._session_id = None
        self._user_id = None
        self._context = {}
        self._cause = None
        self._workflow_operation = None
        self._workflow_step = None
        self._tags = []
    
    def with_error_id(self, error_id: str) -> MindFlowErrorBuilder:
        """Set custom error ID."""
        self._error_id = error_id
        return self
    
    def for_component(self, component: str) -> MindFlowErrorBuilder:
        """Set component where error occurred."""
        self._component = component
        return self
    
    def in_session(self, session_id: str) -> MindFlowErrorBuilder:
        """Set session ID."""
        self._session_id = session_id
        return self
    
    def for_user(self, user_id: str) -> MindFlowErrorBuilder:
        """Set user ID."""
        self._user_id = user_id
        return self
    
    def with_context(self, **context: Any) -> MindFlowErrorBuilder:
        """Add context information."""
        self._context.update(context)
        return self
    
    def caused_by(self, cause: Exception) -> MindFlowErrorBuilder:
        """Set cause exception."""
        self._cause = cause
        return self
    
    def in_workflow(self, operation: str, step: str) -> MindFlowErrorBuilder:
        """Set workflow tracking information."""
        self._workflow_operation = operation
        self._workflow_step = step
        return self
    
    def with_tags(self, *tags: str) -> MindFlowErrorBuilder:
        """Add tags for categorization."""
        self._tags.extend(tags)
        return self
    
    def with_schema(self, schema_class: Type[ErrorSchema]) -> MindFlowErrorBuilder:
        """Associate with a schema class for auto-conversion."""
        self._schema_class = schema_class
        return self
    
    def build(self) -> MindFlowError:
        """Build the MindFlowError instance."""
        # Create base exception
        exception = self._exception_class(
            self._message,
            error_id=self._error_id,
            component=self._component,
            session_id=self._session_id,
            user_id=self._user_id,
            context=self._context,
            cause=self._cause,
        )
        
        # Add enhanced attributes
        if hasattr(exception, '_workflow_operation'):
            exception._workflow_operation = self._workflow_operation
            exception._workflow_step = self._workflow_step
            exception._tags = self._tags
        
        # Store schema class for auto-conversion
        if hasattr(exception, '_schema_class'):
            exception._schema_class = getattr(self, '_schema_class', None)
        
        return exception


class BusinessErrorBuilder(MindFlowErrorBuilder):
    """Builder for BusinessLogicError exceptions with additional business context."""
    
    def __init__(self, message: str, exception_class: Type[BusinessLogicError]):
        super().__init__(message, exception_class)
        self._user_message = None
        self._error_code = None
        self._severity = "low"
        self._recoverable = True
        self._suggestion = None
        self._business_context = {}
    
    def with_user_message(self, user_message: str) -> BusinessErrorBuilder:
        """Set user-friendly message."""
        self._user_message = user_message
        return self
    
    def with_error_code(self, error_code: str) -> BusinessErrorBuilder:
        """Set business error code."""
        self._error_code = error_code
        return self
    
    def with_severity(self, severity: str) -> BusinessErrorBuilder:
        """Set error severity."""
        self._severity = severity
        return self
    
    def set_recoverable(self, recoverable: bool) -> BusinessErrorBuilder:
        """Set whether error is recoverable."""
        self._recoverable = recoverable
        return self
    
    def with_suggestion(self, suggestion: str) -> BusinessErrorBuilder:
        """Add recovery suggestion."""
        self._suggestion = suggestion
        return self
    
    def with_business_context(self, **context: Any) -> BusinessErrorBuilder:
        """Add business-specific context."""
        self._business_context.update(context)
        return self
    
    def build(self) -> BusinessLogicError:
        """Build the BusinessLogicError instance."""
        # Create base exception
        exception = super().build()
        
        # Add business-specific attributes
        exception.user_message = self._user_message or self._message
        exception.error_code = self._error_code
        exception.severity = self._severity
        exception.recoverable = self._recoverable
        exception.suggestion = self._suggestion
        exception.business_context = self._business_context
        
        return exception


class ValidationErrorBuilder(BusinessErrorBuilder):
    """Specialized builder for ValidationError exceptions."""
    
    def __init__(self, message: str, exception_class: Type):
        super().__init__(message, exception_class)
        self._field = None
        self._value = None
        self._validation_rule = None
        self._expected_type = None
        self._expected_format = None
    
    def for_field(self, field: str) -> ValidationErrorBuilder:
        """Set field that failed validation."""
        self._field = field
        return self
    
    def with_value(self, value: Any) -> ValidationErrorBuilder:
        """Set the value that failed validation."""
        self._value = value
        return self
    
    def with_rule(self, validation_rule: str) -> ValidationErrorBuilder:
        """Set validation rule that failed."""
        self._validation_rule = validation_rule
        return self
    
    def expecting_type(self, expected_type: str) -> ValidationErrorBuilder:
        """Set expected data type."""
        self._expected_type = expected_type
        return self
    
    def expecting_format(self, expected_format: str) -> ValidationErrorBuilder:
        """Set expected format."""
        self._expected_format = expected_format
        return self
    
    def build(self) -> Exception:
        """Build the ValidationError instance."""
        # Create base exception
        exception = super().build()
        
        # Add validation-specific attributes
        exception.field = self._field
        exception.value = self._value
        exception.validation_rule = self._validation_rule
        exception.expected_type = self._expected_type
        exception.expected_format = self._expected_format
        
        return exception


class ExceptionTemplates:
    """Pre-built templates for common error scenarios."""
    
    @staticmethod
    def missing_required_field(field: str, value: Any = None) -> ValidationErrorBuilder:
        """Template for missing required field errors."""
        return ValidationErrorBuilder(
            f"Missing required field: {field}",
            ValidationError
        ).for_field(field).with_value(value).with_user_message(
            f"Please provide the {field}"
        ).with_suggestion(f"Add the {field} field to your request").expecting_type("string")
    
    @staticmethod
    def invalid_format(field: str, value: Any, expected_format: str) -> ValidationErrorBuilder:
        """Template for invalid format errors."""
        return ValidationErrorBuilder(
            f"Invalid format for {field}: {value}",
            ValidationError
        ).for_field(field).with_value(value).expecting_format(expected_format).with_user_message(
            f"The {field} field must be in {expected_format} format"
        ).with_suggestion(f"Please provide {field} in valid {expected_format} format")
    
    @staticmethod
    def authentication_failed(auth_method: str, user_identifier: str = None) -> BusinessErrorBuilder:
        """Template for authentication failures."""
        message = f"Authentication failed using {auth_method}"
        if user_identifier:
            message += f" for user {user_identifier}"
        
        return BusinessErrorBuilder(
            message,
            AuthenticationError
        ).with_error_code("AUTH_FAILED").with_severity("medium").with_user_message(
            "Invalid credentials. Please check your username and password."
        ).with_suggestion("Try again or reset your password if you've forgotten it.").with_context(
            auth_method=auth_method,
            user_identifier=user_identifier
        )
    
    @staticmethod
    def access_denied(resource: str, required_permission: str) -> BusinessErrorBuilder:
        """Template for access denied errors."""
        return BusinessErrorBuilder(
            f"Access denied to {resource}",
            AuthorizationError
        ).with_error_code("ACCESS_DENIED").with_severity("medium").with_user_message(
            "You don't have permission to perform this action."
        ).with_suggestion("Contact your administrator if you need access.").with_context(
            resource=resource,
            required_permission=required_permission
        )
    
    @staticmethod
    def resource_not_found(resource_type: str, resource_id: str) -> BusinessErrorBuilder:
        """Template for resource not found errors."""
        return BusinessErrorBuilder(
            f"{resource_type} with ID {resource_id} not found",
            NotFoundError
        ).with_error_code("NOT_FOUND").with_user_message(
            f"The requested {resource_type.lower()} could not be found."
        ).with_suggestion(f"Check the {resource_type.lower()} ID and try again.").with_context(
            resource_type=resource_type,
            resource_id=resource_id
        )
    
    @staticmethod
    def network_failure(endpoint: str, timeout: float = None) -> MindFlowErrorBuilder:
        """Template for network failure errors."""
        message = f"Failed to connect to {endpoint}"
        if timeout:
            message += f" (timeout: {timeout}s)"
        
        return MindFlowErrorBuilder(
            message,
            NetworkError
        ).with_error_code("NETWORK_FAILURE").with_severity("medium").set_recoverable(True).with_user_message(
            "Unable to connect to the service. Please try again later."
        ).with_suggestion("Check your internet connection and try again.").with_context(
            endpoint=endpoint,
            timeout=timeout
        )
    
    @staticmethod
    def service_unavailable(service_name: str, recovery_time: float = None) -> MindFlowErrorBuilder:
        """Template for service unavailable errors."""
        message = f"Service {service_name} is currently unavailable"
        if recovery_time:
            message += f" (estimated recovery: {recovery_time}s)"
        
        return MindFlowErrorBuilder(
            message,
            InfrastructureError
        ).with_error_code("SERVICE_UNAVAILABLE").with_severity("high").set_recoverable(True).with_user_message(
            f"The {service_name} service is temporarily unavailable."
        ).with_suggestion("Please try again in a few minutes.").with_context(
            service_name=service_name,
            estimated_recovery_time=recovery_time
        )


@contextmanager
def ErrorContext(
    operation: str,
    component: str,
    *,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    track_performance: bool = True,
    capture_inputs: bool = False,
    enable_retry: bool = True,
    max_retries: int = 3,
    auto_schema_conversion: bool = True,
):
    """Context manager for enhanced error tracking and management.
    
    Args:
        operation: Operation being performed
        component: Component where operation occurs
        session_id: Session identifier
        user_id: User identifier
        track_performance: Whether to track performance metrics
        capture_inputs: Whether to capture input parameters
        enable_retry: Whether to enable automatic retry
        max_retries: Maximum retry attempts
        auto_schema_conversion: Whether to auto-convert exceptions to schemas
    
    Yields:
        Enhanced error context manager
    """
    context = {
        "operation": operation,
        "component": component,
        "session_id": session_id,
        "user_id": user_id,
        "track_performance": track_performance,
        "capture_inputs": capture_inputs,
        "enable_retry": enable_retry,
        "max_retries": max_retries,
        "auto_schema_conversion": auto_schema_conversion,
        "start_time": datetime.utcnow(),
        "retry_count": 0,
    }
    
    try:
        yield context
    except Exception as exc:
        # Enhance exception with context
        if hasattr(exc, 'context'):
            exc.context.update(context)
        else:
            exc.context = context
        
        # Add workflow tracking if supported
        if hasattr(exc, 'track_workflow'):
            exc.track_workflow(operation, step="error")
        
        # Auto-convert to schema if enabled
        if auto_schema_conversion and hasattr(exc, 'to_schema'):
            try:
                schema = exc.to_schema()
                exc._schema = schema
            except:
                pass  # Schema conversion failed, continue with exception
        
        # Log enhanced error
        _log_enhanced_error(exc, context)
        
        # Retry logic if enabled
        if enable_retry and context["retry_count"] < max_retries and _should_retry(exc):
            context["retry_count"] += 1
            # Re-raise for retry logic to handle
            raise
        else:
            raise


def _log_enhanced_error(exception: Exception, context: Dict[str, Any]) -> None:
    """Log enhanced error with context."""
    import structlog
    
    logger = structlog.get_logger()
    
    log_data = {
        "error_id": getattr(exception, 'error_id', None),
        "error_type": exception.__class__.__name__,
        "message": str(exception),
        "operation": context.get("operation"),
        "component": context.get("component"),
        "session_id": context.get("session_id"),
        "user_id": context.get("user_id"),
        "retry_count": context.get("retry_count", 0),
        "duration": (datetime.utcnow() - context.get("start_time", datetime.utcnow())).total_seconds(),
    }
    
    # Add exception context if available
    if hasattr(exception, 'context'):
        log_data.update(exception.context)
    
    # Add workflow tracking if available
    if hasattr(exception, '_workflow_operation'):
        log_data["workflow_operation"] = exception._workflow_operation
        log_data["workflow_step"] = getattr(exception, '_workflow_step', None)
    
    # Add tags if available
    if hasattr(exception, '_tags'):
        log_data["tags"] = exception._tags
    
    logger.error("Enhanced error occurred", **log_data)


def _should_retry(exception: Exception) -> bool:
    """Determine if an exception should be retried."""
    # Default retry logic - can be extended
    retryable_exceptions = [
        "NetworkError",
        "TimeoutError", 
        "ConnectionError",
        "TemporaryFailure"
    ]
    
    return any(exc_type in exception.__class__.__name__ for exc_type in retryable_exceptions)


# Mixin classes for enhanced functionality

class WorkflowTrackingMixin:
    """Mixin for workflow tracking capabilities."""
    
    def track_workflow(self, operation: str, step: str) -> None:
        """Add workflow tracking information."""
        if not hasattr(self, '_workflow_operation'):
            self._workflow_operation = operation
            self._workflow_step = step
            self._workflow_start_time = datetime.utcnow()
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow tracking information."""
        return {
            "operation": getattr(self, '_workflow_operation', None),
            "step": getattr(self, '_workflow_step', None),
            "start_time": getattr(self, '_workflow_start_time', None),
            "duration": (
                (datetime.utcnow() - self._workflow_start_time).total_seconds()
                if hasattr(self, '_workflow_start_time') else None
            )
        }


class SchemaConversionMixin:
    """Mixin for schema conversion capabilities."""
    
    def to_schema(self) -> ErrorSchema:
        """Convert exception to corresponding schema."""
        # This would be implemented in each exception class
        # Default implementation tries to find matching schema
        from ..schemas.errors import ErrorSchema, ErrorCategory, ErrorSeverity
        
        # Determine category and severity
        category = self._determine_category()
        severity = self._determine_severity()
        
        # Create base schema
        return ErrorSchema.from_exception(
            self,
            category=category,
            severity=severity,
            error_code=getattr(self, 'error_code', 'UNKNOWN'),
            component=getattr(self, 'component', 'unknown'),
            user_message=getattr(self, 'user_message', str(self)),
        )
    
    def _determine_category(self) -> ErrorCategory:
        """Determine error category."""
        # Default implementation - would be overridden in subclasses
        return ErrorCategory.SYSTEM
    
    def _determine_severity(self) -> ErrorSeverity:
        """Determine error severity."""
        # Default implementation - would be overridden in subclasses
        return getattr(self, 'severity', ErrorSeverity.MEDIUM)


class UserMessagingMixin:
    """Mixin for user-friendly messaging."""
    
    def as_user_error(self) -> Dict[str, Any]:
        """Convert to user-friendly error response."""
        return {
            "message": getattr(self, 'user_message', str(self)),
            "error_code": getattr(self, 'error_code', None),
            "suggestion": getattr(self, 'suggestion', None),
            "recoverable": getattr(self, 'recoverable', False),
            "field": getattr(self, 'field', None),
        }
    
    def with_suggestion(self, suggestion: str) -> Exception:
        """Add recovery suggestion."""
        self.suggestion = suggestion
        return self
