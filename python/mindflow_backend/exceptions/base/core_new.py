"""Simplified core exceptions for MindFlow.

Following best practices from examples - simple, direct, and practical.
Provides essential functionality without over-engineering.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ..schemas.errors import ErrorSchema


class MindFlowError(Exception):
    """Base exception for all MindFlow system errors.
    
    Simplified version following examples pattern - essential context
    without over-engineering. Provides structured error information
    including unique ID, component, and basic context.
    """
    
    def __init__(
        self,
        message: str,
        *,
        component: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.error_id = str(uuid.uuid4())
        self.component = component
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
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }
    
    # Simple fluent interface - optional, not required
    def with_context(self, **context: Any) -> MindFlowError:
        """Add context information (optional)."""
        self.context.update(context)
        return self
    
    def caused_by(self, cause: Exception) -> MindFlowError:
        """Set cause exception (optional)."""
        self.cause = cause
        return self
    
    def to_schema(self) -> Optional[ErrorSchema]:
        """Convert to corresponding Pydantic schema."""
        if TYPE_CHECKING:
            from ..schemas.errors import ErrorSchema, ErrorCategory, ErrorSeverity
            return ErrorSchema.from_exception(
                self,
                category=self._determine_category(),
                severity=self._determine_severity(),
                error_code=getattr(self, 'error_code', 'UNKNOWN'),
                component=self.component or 'unknown',
                user_message=getattr(self, 'user_message', str(self)),
            )
        return None
    
    def _determine_category(self) -> str:
        """Determine error category based on exception type."""
        # Simplified category mapping
        if 'Network' in self.__class__.__name__:
            return 'network'
        elif 'Timeout' in self.__class__.__name__:
            return 'timeout'
        elif 'Resource' in self.__class__.__name__:
            return 'resource'
        elif 'Validation' in self.__class__.__name__:
            return 'validation'
        elif 'Authentication' in self.__class__.__name__:
            return 'authentication'
        elif 'Authorization' in self.__class__.__name__:
            return 'authorization'
        else:
            return 'system'
    
    def _determine_severity(self) -> str:
        """Determine error severity based on exception type."""
        # Simplified severity mapping
        if 'Validation' in self.__class__.__name__:
            return 'low'
        elif 'Authentication' in self.__class__.__name__:
            return 'medium'
        elif 'Network' in self.__class__.__name__:
            return 'medium'
        elif 'Timeout' in self.__class__.__name__:
            return 'medium'
        elif 'Resource' in self.__class__.__name__:
            return 'high'
        else:
            return 'medium'


class SystemError(MindFlowError):
    """Base exception for system-level errors.
    
    Simplified for infrastructure, configuration, and operational errors.
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, component="system", **kwargs)


class BusinessLogicError(MindFlowError):
    """Business logic validation and rule violations."""
    
    def __init__(self, message: str, *, domain: Optional[str] = None, **kwargs):
        super().__init__(message, component="business", **kwargs)
        self.domain = domain


class InfrastructureError(SystemError):
    """Infrastructure-related errors (network, database, etc.)."""
    
    def __init__(self, message: str, *, service: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.service = service


class NetworkError(InfrastructureError):
    """Network connectivity errors."""
    
    def __init__(self, message: str, *, endpoint: Optional[str] = None, **kwargs):
        super().__init__(message, service="network", **kwargs)
        self.endpoint = endpoint


class TimeoutError(SystemError):
    """Operation timeout errors."""
    
    def __init__(self, message: str, *, timeout_seconds: Optional[float] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds


class ResourceError(SystemError):
    """Resource exhaustion or unavailability errors."""
    
    def __init__(self, message: str, *, resource_type: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.resource_type = resource_type


# Factory methods for common error patterns following examples
class ErrorFactory:
    """Factory methods for common error patterns."""
    
    @staticmethod
    def network_failure(endpoint: str, cause: Exception = None) -> NetworkError:
        """Create network failure error."""
        return NetworkError(
            f"Network failure accessing {endpoint}",
            endpoint=endpoint,
            cause=cause
        )
    
    @staticmethod
    def timeout(operation: str, timeout_seconds: float) -> TimeoutError:
        """Create timeout error."""
        return TimeoutError(
            f"Operation {operation} timed out after {timeout_seconds}s",
            timeout_seconds=timeout_seconds
        )
    
    @staticmethod
    def resource_exhausted(resource: str) -> ResourceError:
        """Create resource exhaustion error."""
        return ResourceError(
            f"Resource {resource} exhausted",
            resource_type=resource
        )
    
    @staticmethod
    def infrastructure_failure(service: str, operation: str, error_message: str = None) -> InfrastructureError:
        """Create infrastructure failure error."""
        message = f"Infrastructure failure in {service} during {operation}"
        if error_message:
            message += f": {error_message}"
        return InfrastructureError(
            message,
            service=service
        )
    
    @staticmethod
    def system_error(component: str, error_message: str) -> SystemError:
        """Create system error."""
        return SystemError(
            f"System error in {component}: {error_message}",
            context={"component": component}
        )
