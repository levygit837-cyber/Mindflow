"""Common API schemas and base models."""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model with common fields."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    success: bool = True
    message: str | None = None
    timestamp: str | None = None


class ErrorResponse(BaseResponse):
    """Error response model."""
    
    success: bool = False
    error_code: str | None = None
    error_detail: str | None = None
    request_id: str | None = None


class PaginationParams(BaseModel):
    """Pagination parameters for list requests."""
    
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum items per page")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class PaginationResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    
    items: list[T]
    total: int = Field(description="Total number of items")
    limit: int = Field(description="Items per page")
    offset: int = Field(description="Items skipped")
    has_next: bool = Field(description="Whether there are more items")
    has_prev: bool = Field(description="Whether there are previous items")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(default="ok")
    version: str | None = None
    timestamp: str | None = None
    checks: dict[str, Any] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    """Generic status response."""
    
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    
    success: bool = False
    error_type: str = Field(default="validation_error")
    errors: list[dict[str, Any]] = Field(description="List of validation errors")
    request_id: str | None = None


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response."""
    
    success: bool = False
    error_type: str = Field(default="rate_limit_exceeded")
    retry_after: int | None = Field(description="Seconds to wait before retrying")
    limit: int | None = Field(description="Rate limit threshold")
    window: int | None = Field(description="Rate limit window in seconds")
