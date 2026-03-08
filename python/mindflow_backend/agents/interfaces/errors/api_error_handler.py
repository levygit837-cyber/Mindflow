"""API error handler interface.

Defines contracts for handling API-specific errors including routing
failures, authentication/authorization issues, and request processing errors.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Union
from abc import abstractmethod

from mindflow_backend.schemas.errors import (
    RoutingErrorSchema,
    RequestValidationErrorSchema,
    AuthenticationErrorSchema,
    AuthorizationErrorSchema,
    StreamingErrorSchema,
    RateLimitErrorSchema,
    ApiTimeoutErrorSchema,
    ErrorCategory,
    ErrorSeverity,
)

from .base_error_handler import BaseErrorHandlerContract


@runtime_checkable
class APIErrorHandlerContract(BaseErrorHandlerContract, Protocol):
    """Contract for API error handling.
    
    Specialized interface for handling API routing errors, authentication
    failures, authorization issues, and request processing problems.
    """

    @abstractmethod
    async def handle_routing_error(
        self,
        exception: Exception,
        *,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        route_pattern: Optional[str] = None,
        handler_name: Optional[str] = None,
        routing_config: Optional[Dict[str, Any]] = None,
        **context: Any,
    ) -> RoutingErrorSchema:
        """Handle API routing errors.
        
        Args:
            exception: The routing exception
            endpoint: API endpoint that failed routing
            http_method: HTTP method (GET, POST, etc.)
            route_pattern: Route pattern that was matched
            handler_name: Expected handler name
            routing_config: Routing configuration
            **context: Additional context
            
        Returns:
            Routing error schema with routing context
        """
        ...

    @abstractmethod
    async def handle_request_validation_error(
        self,
        exception: Exception,
        *,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        field_errors: Optional[Dict[str, str]] = None,
        missing_fields: Optional[List[str]] = None,
        invalid_fields: Optional[List[str]] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        **context: Any,
    ) -> RequestValidationErrorSchema:
        """Handle API request validation errors.
        
        Args:
            exception: The validation exception
            validation_errors: Detailed validation errors
            field_errors: Field-specific error messages
            missing_fields: Missing required fields
            invalid_fields: Invalid field names
            endpoint: API endpoint being validated
            http_method: HTTP method
            **context: Additional context
            
        Returns:
            Request validation error schema with validation context
        """
        ...

    @abstractmethod
    async def handle_authentication_error(
        self,
        exception: Exception,
        *,
        auth_method: Optional[str] = None,
        auth_provider: Optional[str] = None,
        token_info: Optional[Dict[str, Any]] = None,
        auth_endpoint: Optional[str] = None,
        failure_reason: Optional[str] = None,
        **context: Any,
    ) -> AuthenticationErrorSchema:
        """Handle API authentication errors.
        
        Args:
            exception: The authentication exception
            auth_method: Authentication method used
            auth_provider: Authentication provider
            token_info: Token information
            auth_endpoint: Authentication endpoint
            failure_reason: Specific authentication failure reason
            **context: Additional context
            
        Returns:
            Authentication error schema with auth context
        """
        ...

    @abstractmethod
    async def handle_authorization_error(
        self,
        exception: Exception,
        *,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        user_permissions: Optional[List[str]] = None,
        access_level: Optional[str] = None,
        role: Optional[str] = None,
        **context: Any,
    ) -> AuthorizationErrorSchema:
        """Handle API authorization errors.
        
        Args:
            exception: The authorization exception
            required_permission: Required permission
            resource: Resource being accessed
            user_permissions: User's current permissions
            access_level: Required access level
            role: User role
            **context: Additional context
            
        Returns:
            Authorization error schema with permission context
        """
        ...

    @abstractmethod
    async def handle_streaming_error(
        self,
        exception: Exception,
        *,
        stream_type: Optional[str] = None,
        stream_id: Optional[str] = None,
        connection_info: Optional[Dict[str, Any]] = None,
        client_info: Optional[Dict[str, Any]] = None,
        bytes_sent: Optional[int] = None,
        duration: Optional[float] = None,
        **context: Any,
    ) -> StreamingErrorSchema:
        """Handle API streaming errors.
        
        Args:
            exception: The streaming exception
            stream_type: Type of stream (WebSocket, SSE, etc.)
            stream_id: Stream identifier
            connection_info: Connection information
            client_info: Client information
            bytes_sent: Number of bytes sent before failure
            duration: Stream duration before failure
            **context: Additional context
            
        Returns:
            Streaming error schema with streaming context
        """
        ...

    @abstractmethod
    async def handle_rate_limit_error(
        self,
        exception: Exception,
        *,
        rate_limit: Optional[int] = None,
        period: Optional[int] = None,
        current_usage: Optional[int] = None,
        reset_time: Optional[Any] = None,
        client_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **context: Any,
    ) -> RateLimitErrorSchema:
        """Handle API rate limiting errors.
        
        Args:
            exception: The rate limit exception
            rate_limit: Rate limit (requests per period)
            period: Rate limit period in seconds
            current_usage: Current usage count
            reset_time: When rate limit resets
            client_id: Client identifier
            ip_address: Client IP address
            **context: Additional context
            
        Returns:
            Rate limit error schema with rate limit context
        """
        ...

    @abstractmethod
    async def handle_api_timeout_error(
        self,
        exception: Exception,
        *,
        timeout_seconds: Optional[float] = None,
        elapsed_time: Optional[float] = None,
        timeout_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        **context: Any,
    ) -> ApiTimeoutErrorSchema:
        """Handle API timeout errors.
        
        Args:
            exception: The timeout exception
            timeout_seconds: Timeout limit in seconds
            elapsed_time: Actual elapsed time
            timeout_type: Type of timeout
            endpoint: Timed-out endpoint
            http_method: HTTP method
            **context: Additional context
            
        Returns:
            API timeout error schema with timeout context
        """
        ...

    @abstractmethod
    def get_api_health_status(
        self,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get API health status.
        
        Args:
            endpoint: Specific endpoint to check
            
        Returns:
            API health status information
        """
        ...

    @abstractmethod
    def get_rate_limit_status(
        self,
        client_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get rate limiting status for a client.
        
        Args:
            client_id: Client identifier
            ip_address: Client IP address
            endpoint: Specific endpoint
            
        Returns:
            Rate limiting status information
        """
        ...

    @abstractmethod
    def validate_api_permissions(
        self,
        user_id: str,
        endpoint: str,
        http_method: str,
        resource_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate API permissions for a user.
        
        Args:
            user_id: User identifier
            endpoint: API endpoint
            http_method: HTTP method
            resource_id: Resource identifier
            
        Returns:
            Permission validation results
        """
        ...

    @abstractmethod
    def get_authentication_info(
        self,
        token: str,
        auth_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get authentication information from token.
        
        Args:
            token: Authentication token
            auth_method: Authentication method
            
        Returns:
            Authentication information
        """
        ...

    @abstractmethod
    def log_api_request(
        self,
        request_info: Dict[str, Any],
        response_info: Optional[Dict[str, Any]] = None,
        error_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log API request information.
        
        Args:
            request_info: Request information
            response_info: Response information (if available)
            error_info: Error information (if available)
        """
        ...

    # API-specific convenience methods
    
    def get_api_metrics(
        self,
        endpoint: Optional[str] = None,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get API metrics for monitoring.
        
        Args:
            endpoint: Specific endpoint to get metrics for
            time_range: Time range for metrics (1m, 5m, 15m, 1h, etc.)
            
        Returns:
            API metrics
        """
        # Default implementation - subclasses should override
        return {
            "endpoint": endpoint,
            "time_range": time_range,
            "metrics": {
                "request_count": 0,
                "error_count": 0,
                "average_response_time": 0.0,
                "success_rate": 0.0,
                "status_codes": {},
            }
        }

    def analyze_api_errors(
        self,
        time_range: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze API error patterns.
        
        Args:
            time_range: Time range for analysis (1h, 24h, 7d, etc.)
            endpoint: Specific endpoint to analyze
            
        Returns:
            API error analysis
        """
        # Default implementation - subclasses should override
        return {
            "time_range": time_range,
            "endpoint": endpoint,
            "total_errors": 0,
            "error_types": {},
            "peak_error_times": [],
            "common_endpoints": [],
            "trending_errors": [],
            "recommendations": [],
        }

    def get_api_documentation(
        self,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get API documentation for endpoints.
        
        Args:
            endpoint: Specific endpoint to get docs for
            
        Returns:
            API documentation
        """
        # Default implementation - subclasses should override
        return {
            "endpoint": endpoint,
            "method": "GET",
            "description": "API endpoint documentation",
            "parameters": [],
            "responses": {},
            "authentication_required": True,
            "rate_limits": {},
        }

    def create_api_error_report(
        self,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        include_details: bool = True,
    ) -> Dict[str, Any]:
        """Create comprehensive API error report.
        
        Args:
            start_time: Report start time
            end_time: Report end time
            include_details: Include detailed error information
            
        Returns:
            API error report
        """
        # Default implementation - subclasses should override
        return {
            "report_period": {
                "start": start_time,
                "end": end_time,
            },
            "summary": {
                "total_requests": 0,
                "total_errors": 0,
                "error_rate": 0.0,
                "average_response_time": 0.0,
            },
            "error_breakdown": {},
            "top_errors": [],
            "recommendations": [],
        }

    def test_endpoint_connectivity(
        self,
        endpoint: str,
        http_method: str = "GET",
        *,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Test connectivity to an API endpoint.
        
        Args:
            endpoint: API endpoint to test
            http_method: HTTP method to use
            timeout: Test timeout
            headers: Request headers
            
        Returns:
            Connectivity test results
        """
        # Default implementation - subclasses should override
        return {
            "endpoint": endpoint,
            "method": http_method,
            "connectivity": "unknown",
            "response_time": None,
            "status_code": None,
            "error": None,
            "timestamp": None,
        }
