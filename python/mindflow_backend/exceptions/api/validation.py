"""API validation exceptions.

Exceptions for request validation, parameter validation,
and data format errors in API requests.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business import ValidationError


class RequestValidationError(ValidationError):
    """API request validation failure."""
    
    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        method: str | None = None,
        content_type: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            component="api",
            **kwargs
        )
        self.endpoint = endpoint
        self.method = method
        self.content_type = content_type
