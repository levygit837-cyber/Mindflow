"""FastAPI error handling middleware.

Provides centralized error handling for all API endpoints with
structured error responses and proper logging.
"""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.errors import (
    ErrorCategory,
    ErrorSchema,
    ErrorSeverity,
    ErrorResponse,
)

_logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware for FastAPI."""
    
    def __init__(self, app, *, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Handle all exceptions and return structured error responses."""
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as exc:
            # Create error schema from exception
            error_schema = self._create_error_schema(exc, request)
            
            # Log the error
            self._log_error(error_schema, request)
            
            # Return structured error response
            return self._create_error_response(error_schema, request)
    
    def _create_error_schema(self, exception: Exception, request: Request) -> ErrorSchema:
        """Create standardized error schema from exception."""
        
        # Import here to avoid circular imports
        from mindflow_backend.exceptions import MindFlowError
        
        # Determine error category and severity based on exception type
        category, severity = self._classify_exception(exception)
        
        # Generate error code
        error_code = self._generate_error_code(category, exception.__class__.__name__)
        
        # Extract context from request
        context = self._extract_request_context(request)
        
        # If it's our custom exception, extract additional context
        if isinstance(exception, MindFlowError):
            return ErrorSchema.from_exception(
                exception,
                category=category,
                severity=severity,
                error_code=error_code,
                component=exception.component or "api",
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
            component="api",
            context=context,
            user_message=self._get_user_message(exception),
            recoverable=self._is_recoverable(exception),
        )
    
    def _classify_exception(self, exception: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify exception into category and severity."""
        
        exception_name = exception.__class__.__name__.lower()
        
        # Import our exceptions for classification
        from mindflow_backend.exceptions import (
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
    
    def _extract_request_context(self, request: Request) -> dict[str, Any]:
        """Extract relevant context from request."""
        return {
            "method": request.method,
            "url": str(request.url),
            "path_params": request.path_params,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "request_id": request.headers.get("x-request-id"),
        }
    
    def _get_client_ip(self, request: Request) -> str | None:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return None
    
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
    
    def _log_error(self, error_schema: ErrorSchema, request: Request) -> None:
        """Log error with structured information."""
        log_data = {
            "error_id": error_schema.error_id,
            "error_code": error_schema.error_code,
            "category": error_schema.category.value,
            "severity": error_schema.severity.value,
            "message": error_schema.message,
            "component": error_schema.component,
            "method": request.method,
            "url": str(request.url),
            "client_ip": error_schema.context.metadata.get("client_ip"),
        }
        
        # Add user info if available
        if error_schema.context.user_id:
            log_data["user_id"] = error_schema.context.user_id
        
        # Add session info if available
        if error_schema.context.session_id:
            log_data["session_id"] = error_schema.context.session_id
        
        # Choose log level based on severity
        if error_schema.severity == ErrorSeverity.CRITICAL:
            _logger.critical("api_critical_error", **log_data)
        elif error_schema.severity == ErrorSeverity.HIGH:
            _logger.error("api_error", **log_data)
        elif error_schema.severity == ErrorSeverity.MEDIUM:
            _logger.warning("api_warning", **log_data)
        else:
            _logger.info("api_info", **log_data)
    
    def _create_error_response(self, error_schema: ErrorSchema, request: Request) -> JSONResponse:
        """Create JSON response from error schema."""
        
        # Determine HTTP status code based on error category
        status_code = self._get_status_code(error_schema.category)
        
        # Create error response
        error_response = ErrorResponse(
            error=error_schema,
            request_id=request.headers.get("x-request-id"),
        )
        
        # Add debug information if enabled
        if self.debug:
            error_response.data = {
                "debug": True,
                "stack_trace": error_schema.stack_trace,
            }
        
        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(),
        )
    
    def _get_status_code(self, category: ErrorCategory) -> int:
        """Map error category to HTTP status code."""
        
        status_mapping = {
            ErrorCategory.VALIDATION: status.HTTP_400_BAD_REQUEST,
            ErrorCategory.AUTHENTICATION: status.HTTP_401_UNAUTHORIZED,
            ErrorCategory.AUTHORIZATION: status.HTTP_403_FORBIDDEN,
            ErrorCategory.NOT_FOUND: status.HTTP_404_NOT_FOUND,
            ErrorCategory.CONFLICT: status.HTTP_409_CONFLICT,
            ErrorCategory.RATE_LIMIT: status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCategory.NETWORK: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCategory.TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
            ErrorCategory.RESOURCE: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCategory.INFRASTRUCTURE: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCategory.PROVIDER_ERROR: status.HTTP_502_BAD_GATEWAY,
        }
        
        return status_mapping.get(category, status.HTTP_500_INTERNAL_SERVER_ERROR)
