"""Provider-specific error schemas.

Specialized error schemas for LLM provider failures, rate limiting,
and model availability issues.
"""

from __future__ import annotations

from pydantic import Field

from .base import ErrorSchema


class ProviderErrorSchema(ErrorSchema):
    """Base schema for LLM provider errors."""
    
    # Provider information
    provider_name: str = Field(description="Name of the LLM provider")
    provider_type: str | None = Field(default=None, description="Type of provider")
    endpoint: str | None = Field(default=None, description="API endpoint being used")
    
    # Request information
    model_name: str | None = Field(default=None, description="Model being used")
    request_id: str | None = Field(default=None, description="Provider request ID")
    
    # Authentication
    auth_method: str | None = Field(default=None, description="Authentication method used")
    auth_failed: bool = Field(default=False, description="Whether authentication failed")
    
    class Config:
        extra = "allow"


class RateLimitErrorSchema(ProviderErrorSchema):
    """Schema for rate limit exceeded errors."""
    
    # Rate limit details
    limit_type: str | None = Field(default=None, description="Type of rate limit")
    limit_value: int | None = Field(default=None, description="Rate limit value")
    current_usage: int | None = Field(default=None, description="Current usage count")
    
    # Timing information
    reset_time: str | None = Field(default=None, description="When limit resets")
    retry_after_seconds: int | None = Field(default=None, description="Seconds to wait before retry")
    
    # Request details
    request_size: int | None = Field(default=None, description="Size of request")
    token_count: int | None = Field(default=None, description="Number of tokens in request")
    
    # Recovery suggestions
    can_retry: bool = Field(default=True, description="Whether request can be retried")
    suggested_wait_time: int | None = Field(
        default=None, 
        description="Suggested wait time before retry"
    )


class TokenLimitErrorSchema(ProviderErrorSchema):
    """Schema for token limit exceeded errors."""
    
    # Token information
    input_tokens: int = Field(description="Number of input tokens")
    output_tokens: int | None = Field(default=None, description="Number of output tokens")
    total_tokens: int = Field(description="Total tokens used")
    
    # Limits
    model_limit: int | None = Field(default=None, description="Model token limit")
    context_limit: int | None = Field(default=None, description="Context window limit")
    
    # Request details
    messages_count: int | None = Field(default=None, description="Number of messages")
    estimated_response_tokens: int | None = Field(
        default=None, 
        description="Estimated response tokens"
    )
    
    # Recovery options
    can_truncate: bool = Field(default=False, description="Whether input can be truncated")
    suggested_reduction: int | None = Field(
        default=None, 
        description="Suggested token reduction"
    )


class ModelUnavailableErrorSchema(ProviderErrorSchema):
    """Schema for model unavailability errors."""
    
    # Model information
    model_name: str = Field(description="Name of unavailable model")
    model_version: str | None = Field(default=None, description="Model version")
    
    # Availability details
    availability_status: str | None = Field(
        default=None, 
        description="Current availability status"
    )
    expected_availability: str | None = Field(
        default=None, 
        description="When model is expected to be available"
    )
    
    # Alternative suggestions
    alternative_models: list[str] = Field(
        default_factory=list, 
        description="Alternative models that can be used"
    )
    fallback_available: bool = Field(
        default=False, 
        description="Whether fallback model is available"
    )
    
    # Failure reason
    unavailability_reason: str | None = Field(
        default=None, 
        description="Reason for model unavailability"
    )
    maintenance_window: str | None = Field(
        default=None, 
        description="Maintenance window if applicable"
    )


class AuthenticationErrorSchema(ProviderErrorSchema):
    """Schema for provider authentication errors."""
    
    # Authentication details
    auth_method: str = Field(description="Authentication method used")
    credential_type: str | None = Field(default=None, description="Type of credential")
    
    # Failure information
    auth_error_code: str | None = Field(
        default=None, 
        description="Error code from provider"
    )
    auth_error_message: str | None = Field(
        default=None, 
        description="Error message from provider"
    )
    
    # Credential issues
    credential_expired: bool = Field(default=False, description="Whether credentials expired")
    credential_invalid: bool = Field(default=False, description="Whether credentials are invalid")
    permission_denied: bool = Field(default=False, description="Whether permission was denied")
    
    # Recovery suggestions
    can_refresh: bool = Field(default=False, description="Whether credentials can be refreshed")
    reauth_required: bool = Field(default=False, description="Whether re-authentication is required")


class NetworkErrorSchema(ProviderErrorSchema):
    """Schema for provider network errors."""
    
    # Network details
    connection_type: str | None = Field(default=None, description="Type of connection")
    endpoint_url: str | None = Field(default=None, description="Full endpoint URL")
    
    # Timing information
    timeout_seconds: float | None = Field(default=None, description="Timeout in seconds")
    connection_time_ms: int | None = Field(default=None, description="Time to connect")
    
    # Failure details
    network_error_type: str | None = Field(
        default=None, 
        description="Type of network error"
    )
    dns_resolution_failed: bool = Field(default=False, description="Whether DNS resolution failed")
    ssl_error: bool = Field(default=False, description="Whether SSL/TLS error occurred")
    
    # Recovery options
    can_retry: bool = Field(default=True, description="Whether request can be retried")
    retry_strategy: str | None = Field(
        default=None, 
        description="Suggested retry strategy"
    )


class ModelConfigurationErrorSchema(ProviderErrorSchema):
    """Schema for model configuration errors."""
    
    # Configuration details
    configuration_parameter: str = Field(description="Parameter that caused error")
    parameter_value: str | None = Field(default=None, description="Value that was used")
    
    # Validation information
    expected_type: str | None = Field(default=None, description="Expected parameter type")
    allowed_values: list[str] = Field(
        default_factory=list, 
        description="Allowed values for parameter"
    )
    
    # Model constraints
    min_value: float | None = Field(default=None, description="Minimum allowed value")
    max_value: float | None = Field(default=None, description="Maximum allowed value")
    
    # Error details
    validation_error: str | None = Field(
        default=None, 
        description="Validation error message"
    )
    configuration_source: str | None = Field(
        default=None, 
        description="Source of configuration"
    )


class ContentFilterErrorSchema(ProviderErrorSchema):
    """Schema for content filtering/rejection errors."""
    
    # Content details
    content_type: str | None = Field(default=None, description="Type of content filtered")
    filter_reason: str | None = Field(default=None, description="Reason for filtering")
    
    # Filter information
    policy_violated: str | None = Field(default=None, description="Policy that was violated")
    severity_level: str | None = Field(default=None, description="Severity of violation")
    
    # Content information
    content_length: int | None = Field(default=None, description="Length of content")
    content_hash: str | None = Field(default=None, description="Hash of filtered content")
    
    # Recovery options
    can_modify: bool = Field(default=False, description="Whether content can be modified")
    modification_suggestions: list[str] = Field(
        default_factory=list, 
        description="Suggestions for content modification"
    )
