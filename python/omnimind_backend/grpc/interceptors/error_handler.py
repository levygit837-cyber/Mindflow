"""gRPC error handling interceptor.

Provides centralized error handling for gRPC services with
structured error responses and proper logging.
"""

from __future__ import annotations

import traceback
from typing import Any, Callable

import grpc
from grpc import ServicerContext

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.errors import (
    ErrorCategory,
    ErrorSchema,
    ErrorSeverity,
)

_logger = get_logger(__name__)


class ErrorHandlerInterceptor(grpc.ServerInterceptor):
    """Global error handling interceptor for gRPC services."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def intercept_service(
        self,
        continuation: Callable[[Any, ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept service calls and handle exceptions."""
        
        def intercepted_handler(request: Any, context: ServicerContext) -> Any:
            try:
                return continuation(request, context)
            except Exception as exc:
                self._handle_exception(exc, context, handler_call_details)
                raise  # Re-raise after handling
        
        return intercepted_handler
    
    def _handle_exception(
        self,
        exception: Exception,
        context: ServicerContext,
        call_details: grpc.HandlerCallDetails,
    ) -> None:
        """Handle exception and set appropriate gRPC status."""
        
        # Create error schema from exception
        error_schema = self._create_error_schema(exception, call_details)
        
        # Log the error
        self._log_error(error_schema, call_details)
        
        # Set gRPC status code and details
        self._set_grpc_status(context, error_schema)
    
    def _create_error_schema(self, exception: Exception, call_details: grpc.HandlerCallDetails) -> ErrorSchema:
        """Create standardized error schema from exception."""
        
        # Import here to avoid circular imports
        from omnimind_backend.exceptions import OmniMindError
        
        # Determine error category and severity based on exception type
        category, severity = self._classify_exception(exception)
        
        # Generate error code
        error_code = self._generate_error_code(category, exception.__class__.__name__)
        
        # Extract context from gRPC call
        context = self._extract_grpc_context(call_details)
        
        # If it's our custom exception, extract additional context
        if isinstance(exception, OmniMindError):
            return ErrorSchema.from_exception(
                exception,
                category=category,
                severity=severity,
                error_code=error_code,
                component=exception.component or "grpc",
                context=context,
                user_message=getattr(exception, 'user_message', None),
                recoverable=getattr(exception, 'recoverable', True),
            )
        
        # For standard exceptions, create basic error schema
        return ErrorSchema.from_exception(
            exception,
            category=category,
            severity=severity,
            error_code=error_code,
            component="grpc",
            context=context,
            user_message=self._get_user_message(exception),
            recoverable=self._is_recoverable(exception),
        )
    
    def _classify_exception(self, exception: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify exception into category and severity."""
        
        exception_name = exception.__class__.__name__.lower()
        
        # Import our exceptions for classification
        from omnimind_backend.exceptions import (
            ValidationError, AuthenticationError, AuthorizationError,
            NetworkError, TimeoutError, ResourceError,
            ConfigurationError, DatabaseError, ProviderError
        )
        
        # Business logic errors
        if isinstance(exception, (ValidationError, AuthenticationError, AuthorizationError)):
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW
        
        # Network and connectivity issues
        if isinstance(exception, (NetworkError, TimeoutError)):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        # Resource exhaustion
        if isinstance(exception, ResourceError):
            return ErrorCategory.RESOURCE, ErrorSeverity.HIGH
        
        # Configuration issues
        if isinstance(exception, ConfigurationError):
            return ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
        
        # Database issues
        if isinstance(exception, DatabaseError):
            return ErrorCategory.INFRASTRUCTURE, ErrorSeverity.HIGH
        
        # Provider issues
        if isinstance(exception, ProviderError):
            return ErrorCategory.PROVIDER_ERROR, ErrorSeverity.MEDIUM
        
        # Standard Python exceptions
        if "value" in exception_name or "type" in exception_name:
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW
        
        if "key" in exception_name or "index" in exception_name:
            return ErrorCategory.NOT_FOUND, ErrorSeverity.LOW
        
        if "permission" in exception_name or "access" in exception_name:
            return ErrorCategory.AUTHORIZATION, ErrorSeverity.MEDIUM
        
        if "timeout" in exception_name or "deadline" in exception_name:
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
        
        if "connection" in exception_name or "network" in exception_name:
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        # Default to system error
        return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
    
    def _generate_error_code(self, category: ErrorCategory, exception_name: str) -> str:
        """Generate standardized error code."""
        category_prefix = category.value.upper().split('_')[0]
        exception_short = exception_name.replace('Error', '').upper()
        return f"{category_prefix}_{exception_short[:8]}"
    
    def _extract_grpc_context(self, call_details: grpc.HandlerCallDetails) -> dict[str, Any]:
        """Extract relevant context from gRPC call details."""
        return {
            "method": call_details.method,
            "invocation_metadata": dict(call_details.invocation_metadata) if call_details.invocation_metadata else {},
            "client": getattr(call_details, 'client', None),
        }
    
    def _get_user_message(self, exception: Exception) -> str | None:
        """Get user-friendly message for exception."""
        exception_name = exception.__class__.__name__.lower()
        
        if "validation" in exception_name or "value" in exception_name:
            return "The provided data is invalid. Please check your input and try again."
        
        if "authentication" in exception_name:
            return "Authentication failed. Please check your credentials and try again."
        
        if "authorization" in exception_name or "permission" in exception_name:
            return "You don't have permission to perform this action."
        
        if "notfound" in exception_name or "not_found" in exception_name:
            return "The requested resource was not found."
        
        if "timeout" in exception_name:
            return "The request took too long to complete. Please try again."
        
        if "network" in exception_name or "connection" in exception_name:
            return "Network connection failed. Please check your connection and try again."
        
        # Default generic message
        return "An unexpected error occurred. Please try again later."
    
    def _is_recoverable(self, exception: Exception) -> bool:
        """Determine if error is recoverable."""
        exception_name = exception.__class__.__name__.lower()
        
        # Generally recoverable errors
        recoverable_patterns = [
            "timeout", "network", "connection", "rate", "limit",
            "temporary", "transient"
        ]
        
        return any(pattern in exception_name for pattern in recoverable_patterns)
    
    def _log_error(self, error_schema: ErrorSchema, call_details: grpc.HandlerCallDetails) -> None:
        """Log error with structured information."""
        log_data = {
            "error_id": error_schema.error_id,
            "error_code": error_schema.error_code,
            "category": error_schema.category.value,
            "severity": error_schema.severity.value,
            "message": error_schema.message,
            "component": error_schema.component,
            "grpc_method": call_details.method,
        }
        
        # Add user info if available
        if error_schema.context.user_id:
            log_data["user_id"] = error_schema.context.user_id
        
        # Add session info if available
        if error_schema.context.session_id:
            log_data["session_id"] = error_schema.context.session_id
        
        # Add client info if available
        client_info = error_schema.context.metadata.get("client")
        if client_info:
            log_data["client"] = client_info
        
        # Choose log level based on severity
        if error_schema.severity == ErrorSeverity.CRITICAL:
            _logger.critical("grpc_critical_error", **log_data)
        elif error_schema.severity == ErrorSeverity.HIGH:
            _logger.error("grpc_error", **log_data)
        elif error_schema.severity == ErrorSeverity.MEDIUM:
            _logger.warning("grpc_warning", **log_data)
        else:
            _logger.info("grpc_info", **log_data)
    
    def _set_grpc_status(self, context: ServicerContext, error_schema: ErrorSchema) -> None:
        """Set appropriate gRPC status code and error details."""
        
        # Map error category to gRPC status code
        grpc_status = self._get_grpc_status_code(error_schema.category)
        
        # Create error details
        error_details = {
            "error_id": error_schema.error_id,
            "error_code": error_schema.error_code,
            "message": error_schema.user_message or error_schema.message,
            "category": error_schema.category.value,
            "severity": error_schema.severity.value,
            "recoverable": error_schema.recoverable,
        }
        
        # Add debug information if enabled
        if self.debug:
            error_details.update({
                "debug": True,
                "technical_message": error_schema.message,
                "stack_trace": error_schema.stack_trace,
            })
        
        # Set gRPC status with error details
        context.set_code(grpc_status)
        context.set_details(str(error_details))
    
    def _get_grpc_status_code(self, category: ErrorCategory) -> grpc.StatusCode:
        """Map error category to gRPC status code."""
        
        status_mapping = {
            ErrorCategory.VALIDATION: grpc.StatusCode.INVALID_ARGUMENT,
            ErrorCategory.AUTHENTICATION: grpc.StatusCode.UNAUTHENTICATED,
            ErrorCategory.AUTHORIZATION: grpc.StatusCode.PERMISSION_DENIED,
            ErrorCategory.NOT_FOUND: grpc.StatusCode.NOT_FOUND,
            ErrorCategory.CONFLICT: grpc.StatusCode.ALREADY_EXISTS,
            ErrorCategory.RATE_LIMIT: grpc.StatusCode.RESOURCE_EXHAUSTED,
            ErrorCategory.NETWORK: grpc.StatusCode.UNAVAILABLE,
            ErrorCategory.TIMEOUT: grpc.StatusCode.DEADLINE_EXCEEDED,
            ErrorCategory.RESOURCE: grpc.StatusCode.RESOURCE_EXHAUSTED,
            ErrorCategory.INFRASTRUCTURE: grpc.StatusCode.UNAVAILABLE,
            ErrorCategory.PROVIDER_ERROR: grpc.StatusCode.UNAVAILABLE,
            ErrorCategory.SYSTEM: grpc.StatusCode.INTERNAL,
        }
        
        return status_mapping.get(category, grpc.StatusCode.INTERNAL)
