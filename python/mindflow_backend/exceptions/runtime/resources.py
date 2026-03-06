"""Resource management exceptions.

Exceptions for resource exhaustion, memory limits,
and system resource constraints.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core import ResourceError as BaseResourceError


class ResourceError(BaseResourceError):
    """Runtime resource exhaustion."""
    
    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        current_usage: str | None = None,
        limit: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            resource_type=resource_type,
            current_usage=current_usage,
            component="runtime",
            **kwargs
        )
        self.limit = limit
