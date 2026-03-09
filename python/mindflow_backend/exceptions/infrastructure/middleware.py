"""Middleware exceptions.

Exceptions for middleware failures, request processing,
and pipeline execution errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_new import InfrastructureError


class MiddlewareError(InfrastructureError):
    """Middleware execution failure."""
    
    def __init__(
        self,
        message: str,
        *,
        middleware_name: str | None = None,
        middleware_type: str | None = None,
        pipeline_stage: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            service="middleware",
            component="infrastructure",
            **kwargs
        )
        self.middleware_name = middleware_name
        self.middleware_type = middleware_type
        self.pipeline_stage = pipeline_stage
