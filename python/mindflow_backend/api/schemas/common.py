"""Common API schemas and base models.

DEPRECATED: This module has been moved to mindflow_backend.schemas.api.common
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.schemas.api.common import BaseResponse, ErrorResponse, PaginationParams, PaginationResponse, HealthResponse, StatusResponse, ValidationErrorResponse, RateLimitResponse
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.schemas.api.common import (
    BaseResponse,
    ErrorResponse,
    PaginationParams,
    PaginationResponse,
    HealthResponse,
    StatusResponse,
    ValidationErrorResponse,
    RateLimitResponse,
)

# Maintain backward compatibility
__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "PaginationParams",
    "PaginationResponse",
    "HealthResponse",
    "StatusResponse",
    "ValidationErrorResponse",
    "RateLimitResponse",
]
