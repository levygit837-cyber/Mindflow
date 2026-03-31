"""API error schemas for MindFlow.

Specialized schemas for API-related exceptions that were missing from
the original implementation. These provide structured error responses
for API routing and request handling errors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .base import ErrorCategory, ErrorSchema, ErrorSeverity


class RoutingErrorSchema(ErrorSchema):
    """Schema for RoutingError - API routing failures.
    
    Raised when API routing fails to find appropriate handler
    or when routing configuration is invalid.
    """
    
    # RoutingError specific fields
    endpoint: str | None = Field(default=None, description="API endpoint that failed routing")
    http_method: str | None = Field(default=None, description="HTTP method (GET, POST, etc.)")
    route_pattern: str | None = Field(default=None, description="Route pattern that was matched")
    handler_name: str | None = Field(default=None, description="Expected handler name")
    routing_config: dict[str, Any] | None = Field(default=None, description="Routing configuration")
    
    # Request context
    request_path: str | None = Field(default=None, description="Full request path")
    query_params: dict[str, Any] | None = Field(default=None, description="Query parameters")
    headers: dict[str, str] | None = Field(default=None, description="Request headers")
    
    # Alternative routes
    suggested_routes: list[str] | None = Field(default=None, description="Suggested alternative routes")
    similar_endpoints: list[str] | None = Field(default=None, description="Similar available endpoints")
    
    category: ErrorCategory = Field(default=ErrorCategory.ROUTING, description="Routing errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Routing errors are medium severity")
    recoverable: bool = Field(default=True, description="Routing errors are typically recoverable")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class RequestValidationErrorSchema(ErrorSchema):
    """Schema for RequestValidationError - API request validation failures.
    
    Raised when API request validation fails due to invalid input,
    missing required fields, or format errors.
    """
    
    # RequestValidationError specific fields
    validation_errors: list[dict[str, Any]] | None = Field(default=None, description="Detailed validation errors")
    field_errors: dict[str, str] | None = Field(default=None, description="Field-specific error messages")
    missing_fields: list[str] | None = Field(default=None, description="Missing required fields")
    invalid_fields: list[str] | None = Field(default=None, description="Invalid field names")
    
    # Request context
    endpoint: str | None = Field(default=None, description="API endpoint being validated")
    http_method: str | None = Field(default=None, description="HTTP method")
    content_type: str | None = Field(default=None, description="Request content type")
    request_size: int | None = Field(default=None, description="Request size in bytes")
    
    # Validation context
    schema_name: str | None = Field(default=None, description="Validation schema name")
    validation_rules: list[str] | None = Field(default=None, description="Applied validation rules")
    expected_format: str | None = Field(default=None, description="Expected request format")
    
    category: ErrorCategory = Field(default=ErrorCategory.VALIDATION, description="Validation errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.LOW, description="Request validation errors are low severity")
    recoverable: bool = Field(default=True, description="Request validation errors are recoverable")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class AuthenticationErrorSchema(ErrorSchema):
    """Schema for AuthenticationError - API authentication failures.
    
    Raised when API authentication fails due to invalid credentials,
    missing authentication tokens, or authentication service errors.
    """
    
    # AuthenticationError specific fields
    auth_method: str | None = Field(default=None, description="Authentication method used")
    auth_provider: str | None = Field(default=None, description="Authentication provider")
    token_info: dict[str, Any] | None = Field(default=None, description="Token information")
    auth_endpoint: str | None = Field(default=None, description="Authentication endpoint")
    
    # Request context
    endpoint: str | None = Field(default=None, description="Protected endpoint being accessed")
    http_method: str | None = Field(default=None, description="HTTP method")
    required_permissions: list[str] | None = Field(default=None, description="Required permissions")
    
    # Failure details
    failure_reason: str | None = Field(default=None, description="Specific authentication failure reason")
    error_code: str | None = Field(default=None, description="Authentication error code")
    retry_allowed: bool | None = Field(default=None, description="Whether retry is allowed")
    
    category: ErrorCategory = Field(default=ErrorCategory.AUTHENTICATION, description="Authentication errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Authentication errors are medium severity")
    recoverable: bool = Field(default=True, description="Authentication errors are recoverable")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class AuthorizationErrorSchema(ErrorSchema):
    """Schema for AuthorizationError - API authorization failures.
    
    Raised when user lacks permission to access a resource or perform
    an operation, despite having valid authentication.
    """
    
    # AuthorizationError specific fields
    required_permission: str | None = Field(default=None, description="Required permission")
    resource: str | None = Field(default=None, description="Resource being accessed")
    user_permissions: list[str] | None = Field(default=None, description="User's current permissions")
    access_level: str | None = Field(default=None, description="Required access level")
    
    # Request context
    endpoint: str | None = Field(default=None, description="Protected endpoint being accessed")
    http_method: str | None = Field(default=None, description="HTTP method")
    resource_id: str | None = Field(default=None, description="Resource identifier")
    
    # Authorization details
    role: str | None = Field(default=None, description="User role")
    scope: str | None = Field(default=None, description="Authorization scope")
    policy_violated: str | None = Field(default=None, description="Security policy that was violated")
    
    category: ErrorCategory = Field(default=ErrorCategory.AUTHORIZATION, description="Authorization errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Authorization errors are medium severity")
    recoverable: bool = Field(default=True, description="Authorization errors are recoverable")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class StreamingErrorSchema(ErrorSchema):
    """Schema for StreamingError - API streaming failures.
    
    Raised when API streaming operations fail due to connection issues,
    stream interruptions, or streaming protocol errors.
    """
    
    # StreamingError specific fields
    stream_type: str | None = Field(default=None, description="Type of stream (WebSocket, SSE, etc.)")
    stream_id: str | None = Field(default=None, description="Stream identifier")
    connection_info: dict[str, Any] | None = Field(default=None, description="Connection information")
    
    # Stream context
    endpoint: str | None = Field(default=None, description="Streaming endpoint")
    client_info: dict[str, Any] | None = Field(default=None, description="Client information")
    stream_state: str | None = Field(default=None, description="Stream state at error time")
    
    # Failure details
    bytes_sent: int | None = Field(default=None, description="Number of bytes sent before failure")
    duration: float | None = Field(default=None, description="Stream duration before failure")
    retry_count: int | None = Field(default=None, description="Number of retry attempts")
    
    category: ErrorCategory = Field(default=ErrorCategory.NETWORK, description="Streaming errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Streaming errors are medium severity")
    recoverable: bool = Field(default=True, description="Streaming errors are typically recoverable")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class RateLimitErrorSchema(ErrorSchema):
    """Schema for RateLimitError - API rate limiting failures.
    
    Raised when API rate limits are exceeded and requests are throttled.
    """
    
    # RateLimitError specific fields
    rate_limit: int | None = Field(default=None, description="Rate limit (requests per period)")
    period: int | None = Field(default=None, description="Rate limit period in seconds")
    current_usage: int | None = Field(default=None, description="Current usage count")
    reset_time: datetime | None = Field(default=None, description="When rate limit resets")
    
    # Request context
    endpoint: str | None = Field(default=None, description="Rate-limited endpoint")
    client_id: str | None = Field(default=None, description="Client identifier")
    ip_address: str | None = Field(default=None, description="Client IP address")
    
    # Rate limiting details
    limit_type: str | None = Field(default=None, description="Type of rate limit (global, per-user, per-ip)")
    retry_after: int | None = Field(default=None, description="Seconds to wait before retry")
    alternative_endpoints: list[str] | None = Field(default=None, description="Alternative endpoints")
    
    category: ErrorCategory = Field(default=ErrorCategory.RESOURCE, description="Rate limit errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="Rate limit errors are medium severity")
    recoverable: bool = Field(default=True, description="Rate limit errors are recoverable")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ApiTimeoutErrorSchema(ErrorSchema):
    """Schema for API TimeoutError - API request timeout failures.
    
    Raised when API requests timeout due to slow processing,
    network issues, or resource constraints.
    """
    
    # ApiTimeoutError specific fields
    timeout_seconds: float | None = Field(default=None, description="Timeout limit in seconds")
    elapsed_time: float | None = Field(default=None, description="Actual elapsed time")
    timeout_type: str | None = Field(default=None, description="Type of timeout")
    
    # Request context
    endpoint: str | None = Field(default=None, description="Timed-out endpoint")
    http_method: str | None = Field(default=None, description="HTTP method")
    request_size: int | None = Field(default=None, description="Request size in bytes")
    
    # Performance context
    processing_time: float | None = Field(default=None, description="Server processing time")
    network_time: float | None = Field(default=None, description="Network round-trip time")
    queue_time: float | None = Field(default=None, description="Time spent in queue")
    
    category: ErrorCategory = Field(default=ErrorCategory.TIMEOUT, description="Timeout errors category")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="API timeout errors are medium severity")
    recoverable: bool = Field(default=True, description="API timeout errors are recoverable")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
