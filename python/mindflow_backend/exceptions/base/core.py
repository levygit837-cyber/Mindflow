"""Core base exceptions for MindFlow.

Root exceptions that all other system exceptions inherit from.
Provides structured error handling with context and metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas.errors import ErrorSchema
    from .patterns import ExceptionBuilder


class MindFlowError(Exception):
    """Base exception for all MindFlow system errors.
    
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
        
        # Enhanced attributes for fluent interface
        self._workflow_operation = None
        self._workflow_step = None
        self._tags = []
        self._schema_class = None
        
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
    
    # Fluent interface methods
    
    def with_context(self, **context: Any) -> MindFlowError:
        """Fluent interface for adding context."""
        self.context.update(context)
        return self
    
    def track_workflow(self, operation: str, step: str) -> MindFlowError:
        """Add workflow tracking context."""
        self._workflow_operation = operation
        self._workflow_step = step
        self._workflow_start_time = datetime.utcnow()
        return self
    
    def with_user_context(self, user_id: str, session_id: str) -> MindFlowError:
        """Add user tracking context."""
        self.user_id = user_id
        self.session_id = session_id
        return self
    
    def with_tags(self, *tags: str) -> MindFlowError:
        """Add tags for categorization."""
        self._tags.extend(tags)
        return self
    
    def caused_by(self, cause: Exception) -> MindFlowError:
        """Set cause exception."""
        self.cause = cause
        return self
    
    def with_schema(self, schema_class: Type[ErrorSchema]) -> MindFlowError:
        """Associate with a schema class for auto-conversion."""
        self._schema_class = schema_class
        return self
    
    def to_schema(self) -> ErrorSchema:
        """Convert to corresponding Pydantic schema."""
        if self._schema_class:
            return self._schema_class.from_exception(
                self,
                category=self._determine_category(),
                severity=self._determine_severity(),
                error_code=getattr(self, 'error_code', 'UNKNOWN'),
                component=self.component or 'unknown',
                user_message=getattr(self, 'user_message', str(self)),
            )
        
        # Fallback to base schema
        from ..schemas.errors import ErrorSchema, ErrorCategory, ErrorSeverity
        return ErrorSchema.from_exception(
            self,
            category=self._determine_category(),
            severity=self._determine_severity(),
            error_code=getattr(self, 'error_code', 'UNKNOWN'),
            component=self.component or 'unknown',
            user_message=getattr(self, 'user_message', str(self)),
        )
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow tracking information."""
        return {
            "operation": self._workflow_operation,
            "step": self._workflow_step,
            "start_time": getattr(self, '_workflow_start_time', None),
            "duration": (
                (datetime.utcnow() - self._workflow_start_time).total_seconds()
                if hasattr(self, '_workflow_start_time') else None
            ),
            "tags": self._tags,
        }
    
    def as_user_error(self) -> Dict[str, Any]:
        """Convert to user-friendly error response."""
        return {
            "message": getattr(self, 'user_message', str(self)),
            "error_code": getattr(self, 'error_code', None),
            "suggestion": getattr(self, 'suggestion', None),
            "recoverable": getattr(self, 'recoverable', False),
            "error_id": self.error_id,
        }
    
    def _determine_category(self) -> ErrorCategory:
        """Determine error category based on exception type."""
        from ..schemas.errors import ErrorCategory
        
        # Map exception types to categories
        category_mapping = {
            'NetworkError': ErrorCategory.NETWORK,
            'TimeoutError': ErrorCategory.TIMEOUT,
            'ResourceError': ErrorCategory.RESOURCE,
            'ConfigurationError': ErrorCategory.CONFIGURATION,
            'InfrastructureError': ErrorCategory.INFRASTRUCTURE,
            'ValidationError': ErrorCategory.VALIDATION,
            'AuthenticationError': ErrorCategory.AUTHENTICATION,
            'AuthorizationError': ErrorCategory.AUTHORIZATION,
            'BusinessRuleError': ErrorCategory.BUSINESS_RULE,
            'WorkflowError': ErrorCategory.WORKFLOW,
            'NotFoundError': ErrorCategory.NOT_FOUND,
            'ConflictError': ErrorCategory.CONFLICT,
        }
        
        return category_mapping.get(self.__class__.__name__, ErrorCategory.SYSTEM)
    
    def _determine_severity(self) -> ErrorSeverity:
        """Determine error severity based on exception type and attributes."""
        from ..schemas.errors import ErrorSeverity
        
        # Use explicit severity if set
        if hasattr(self, 'severity'):
            severity_map = {
                'low': ErrorSeverity.LOW,
                'medium': ErrorSeverity.MEDIUM,
                'high': ErrorSeverity.HIGH,
                'critical': ErrorSeverity.CRITICAL,
            }
            return severity_map.get(self.severity, ErrorSeverity.MEDIUM)
        
        # Default severity mapping
        severity_mapping = {
            'ValidationError': ErrorSeverity.LOW,
            'BusinessLogicError': ErrorSeverity.LOW,
            'NetworkError': ErrorSeverity.MEDIUM,
            'TimeoutError': ErrorSeverity.MEDIUM,
            'AuthenticationError': ErrorSeverity.MEDIUM,
            'AuthorizationError': ErrorSeverity.MEDIUM,
            'SystemError': ErrorSeverity.HIGH,
            'InfrastructureError': ErrorSeverity.HIGH,
            'ResourceError': ErrorSeverity.HIGH,
        }
        
        return severity_mapping.get(self.__class__.__name__, ErrorSeverity.MEDIUM)
    
    # Builder pattern support
    
    @classmethod
    def builder(cls, message: str) -> ExceptionBuilder:
        """Create a builder for this exception type."""
        from .patterns import MindFlowErrorBuilder
        return MindFlowErrorBuilder(message, cls)
    
    @classmethod
    def create(cls, message: str, **kwargs: Any) -> MindFlowError:
        """Create exception with builder pattern support."""
        return cls.builder(message).with_context(**kwargs).build()


class SystemError(MindFlowError):
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
    
    def with_severity(self, severity: str) -> SystemError:
        """Set error severity."""
        self.severity = severity
        return self
    
    def set_recoverable(self, recoverable: bool) -> SystemError:
        """Set whether error is recoverable."""
        self.recoverable = recoverable
        return self
    
    def for_config_key(self, config_key: str) -> ConfigurationError:
        """Set configuration key."""
        self.config_key = config_key
        return self
    
    def expecting_type(self, expected_type: str) -> ConfigurationError:
        """Set expected configuration type."""
        self.expected_type = expected_type
        return self
    
    def with_actual_value(self, actual_value: Any) -> ConfigurationError:
        """Set actual configuration value."""
        self.actual_value = actual_value
        return self


class InfrastructureError(SystemError):
    """Raised when infrastructure components fail (DB, Redis, etc.)."""
    
    def __init__(
        self,
        message: str,
        *,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        endpoint: Optional[str] = None,
        health_check: Optional[bool] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="high", recoverable=True, **kwargs)
        self.service = service
        self.operation = operation
        self.endpoint = endpoint
        self.health_check = health_check
    
    def for_service(self, service: str) -> InfrastructureError:
        """Set service name."""
        self.service = service
        return self
    
    def in_operation(self, operation: str) -> InfrastructureError:
        """Set operation being performed."""
        self.operation = operation
        return self
    
    def with_endpoint(self, endpoint: str) -> InfrastructureError:
        """Set service endpoint."""
        self.endpoint = endpoint
        return self


class NetworkError(SystemError):
    """Raised when network operations fail."""
    
    def __init__(
        self,
        message: str,
        *,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        retry_count: int = 0,
        network_state: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", recoverable=True, **kwargs)
        self.endpoint = endpoint
        self.timeout = timeout
        self.retry_count = retry_count
        self.network_state = network_state
    
    def for_endpoint(self, endpoint: str) -> NetworkError:
        """Set network endpoint."""
        self.endpoint = endpoint
        return self
    
    def with_timeout(self, timeout: float) -> NetworkError:
        """Set network timeout."""
        self.timeout = timeout
        return self
    
    def with_retry_count(self, retry_count: int) -> NetworkError:
        """Set retry count."""
        self.retry_count = retry_count
        return self


class ResourceError(SystemError):
    """Raised when system resources are exhausted or unavailable."""
    
    def __init__(
        self,
        message: str,
        *,
        resource_type: Optional[str] = None,
        current_usage: Optional[str] = None,
        resource_limit: Optional[str] = None,
        allocation_failure: bool = False,
        **kwargs: Any,
    ):
        super().__init__(message, severity="high", recoverable=False, **kwargs)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.resource_limit = resource_limit
        self.allocation_failure = allocation_failure
    
    def for_resource_type(self, resource_type: str) -> ResourceError:
        """Set resource type."""
        self.resource_type = resource_type
        return self
    
    def with_usage(self, current_usage: str, limit: str) -> ResourceError:
        """Set usage information."""
        self.current_usage = current_usage
        self.resource_limit = limit
        return self


class TimeoutError(SystemError):
    """Raised when operations exceed their time limits."""
    
    def __init__(
        self,
        message: str,
        *,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        elapsed_time: Optional[float] = None,
        timeout_type: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, severity="medium", recoverable=True, **kwargs)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.elapsed_time = elapsed_time
        self.timeout_type = timeout_type
    
    def for_operation(self, operation: str) -> TimeoutError:
        """Set operation that timed out."""
        self.operation = operation
        return self
    
    def with_timeout_duration(self, timeout_seconds: float) -> TimeoutError:
        """Set timeout duration."""
        self.timeout_seconds = timeout_seconds
        return self
    
    def with_elapsed_time(self, elapsed_time: float) -> TimeoutError:
        """Set elapsed time."""
        self.elapsed_time = elapsed_time
        return self


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
