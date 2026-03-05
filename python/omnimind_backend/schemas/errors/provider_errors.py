"""Provider-specific error schemas.

Specialized error schemas for LLM provider failures, rate limiting,
and model availability issues.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from .base import ErrorSchema, ErrorContext, ErrorSeverity


class ProviderErrorSchema(ErrorSchema):
    """Base schema for LLM provider errors."""
    
    # Provider information
    provider_name: str = Field(description="Name of the LLM provider")
    provider_type: Optional[str] = Field(default=None, description="Type of provider")
    endpoint: Optional[str] = Field(default=None, description="API endpoint being used")
    
    # Request information
    model_name: Optional[str] = Field(default=None, description="Model being used")
    request_id: Optional[str] = Field(default=None, description="Provider request ID")
    
    # Authentication
    auth_method: Optional[str] = Field(default=None, description="Authentication method used")
    auth_failed: bool = Field(default=False, description="Whether authentication failed")
    
    class Config:
        extra = "allow"


class RateLimitErrorSchema(ProviderErrorSchema):
    """Schema for rate limit exceeded errors."""
    
    # Rate limit details
    limit_type: Optional[str] = Field(default=None, description="Type of rate limit")
    limit_value: Optional[int] = Field(default=None, description="Rate limit value")
    current_usage: Optional[int] = Field(default=None, description="Current usage count")
    
    # Timing information
    reset_time: Optional[str] = Field(default=None, description="When limit resets")
    retry_after_seconds: Optional[int] = Field(default=None, description="Seconds to wait before retry")
    
    # Request details
    request_size: Optional[int] = Field(default=None, description="Size of request")
    token_count: Optional[int] = Field(default=None, description="Number of tokens in request")
    
    # Recovery suggestions
    can_retry: bool = Field(default=True, description="Whether request can be retried")
    suggested_wait_time: Optional[int] = Field(
        default=None, 
        description="Suggested wait time before retry"
    )


class TokenLimitErrorSchema(ProviderErrorSchema):
    """Schema for token limit exceeded errors."""
    
    # Token information
    input_tokens: int = Field(description="Number of input tokens")
    output_tokens: Optional[int] = Field(default=None, description="Number of output tokens")
    total_tokens: int = Field(description="Total tokens used")
    
    # Limits
    model_limit: Optional[int] = Field(default=None, description="Model token limit")
    context_limit: Optional[int] = Field(default=None, description="Context window limit")
    
    # Request details
    messages_count: Optional[int] = Field(default=None, description="Number of messages")
    estimated_response_tokens: Optional[int] = Field(
        default=None, 
        description="Estimated response tokens"
    )
    
    # Recovery options
    can_truncate: bool = Field(default=False, description="Whether input can be truncated")
    suggested_reduction: Optional[int] = Field(
        default=None, 
        description="Suggested token reduction"
    )


class ModelUnavailableErrorSchema(ProviderErrorSchema):
    """Schema for model unavailability errors."""
    
    # Model information
    model_name: str = Field(description="Name of unavailable model")
    model_version: Optional[str] = Field(default=None, description="Model version")
    
    # Availability details
    availability_status: Optional[str] = Field(
        default=None, 
        description="Current availability status"
    )
    expected_availability: Optional[str] = Field(
        default=None, 
        description="When model is expected to be available"
    )
    
    # Alternative suggestions
    alternative_models: List[str] = Field(
        default_factory=list, 
        description="Alternative models that can be used"
    )
    fallback_available: bool = Field(
        default=False, 
        description="Whether fallback model is available"
    )
    
    # Failure reason
    unavailability_reason: Optional[str] = Field(
        default=None, 
        description="Reason for model unavailability"
    )
    maintenance_window: Optional[str] = Field(
        default=None, 
        description="Maintenance window if applicable"
    )


class AuthenticationErrorSchema(ProviderErrorSchema):
    """Schema for provider authentication errors."""
    
    # Authentication details
    auth_method: str = Field(description="Authentication method used")
    credential_type: Optional[str] = Field(default=None, description="Type of credential")
    
    # Failure information
    auth_error_code: Optional[str] = Field(
        default=None, 
        description="Error code from provider"
    )
    auth_error_message: Optional[str] = Field(
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
    connection_type: Optional[str] = Field(default=None, description="Type of connection")
    endpoint_url: Optional[str] = Field(default=None, description="Full endpoint URL")
    
    # Timing information
    timeout_seconds: Optional[float] = Field(default=None, description="Timeout in seconds")
    connection_time_ms: Optional[int] = Field(default=None, description="Time to connect")
    
    # Failure details
    network_error_type: Optional[str] = Field(
        default=None, 
        description="Type of network error"
    )
    dns_resolution_failed: bool = Field(default=False, description="Whether DNS resolution failed")
    ssl_error: bool = Field(default=False, description="Whether SSL/TLS error occurred")
    
    # Recovery options
    can_retry: bool = Field(default=True, description="Whether request can be retried")
    retry_strategy: Optional[str] = Field(
        default=None, 
        description="Suggested retry strategy"
    )


class ModelConfigurationErrorSchema(ProviderErrorSchema):
    """Schema for model configuration errors."""
    
    # Configuration details
    configuration_parameter: str = Field(description="Parameter that caused error")
    parameter_value: Optional[str] = Field(default=None, description="Value that was used")
    
    # Validation information
    expected_type: Optional[str] = Field(default=None, description="Expected parameter type")
    allowed_values: List[str] = Field(
        default_factory=list, 
        description="Allowed values for parameter"
    )
    
    # Model constraints
    min_value: Optional[float] = Field(default=None, description="Minimum allowed value")
    max_value: Optional[float] = Field(default=None, description="Maximum allowed value")
    
    # Error details
    validation_error: Optional[str] = Field(
        default=None, 
        description="Validation error message"
    )
    configuration_source: Optional[str] = Field(
        default=None, 
        description="Source of configuration"
    )


class ContentFilterErrorSchema(ProviderErrorSchema):
    """Schema for content filtering/rejection errors."""
    
    # Content details
    content_type: Optional[str] = Field(default=None, description="Type of content filtered")
    filter_reason: Optional[str] = Field(default=None, description="Reason for filtering")
    
    # Filter information
    policy_violated: Optional[str] = Field(default=None, description="Policy that was violated")
    severity_level: Optional[str] = Field(default=None, description="Severity of violation")
    
    # Content information
    content_length: Optional[int] = Field(default=None, description="Length of content")
    content_hash: Optional[str] = Field(default=None, description="Hash of filtered content")
    
    # Recovery options
    can_modify: bool = Field(default=False, description="Whether content can be modified")
    modification_suggestions: List[str] = Field(
        default_factory=list, 
        description="Suggestions for content modification"
    )
