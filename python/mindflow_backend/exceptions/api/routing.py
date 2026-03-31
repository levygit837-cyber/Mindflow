"""API routing exceptions.

Exceptions for endpoint routing, URL resolution,
and request dispatching errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business_new import BusinessLogicError


class RoutingError(BusinessLogicError):
    """API routing failure."""
    
    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        method: str | None = None,
        handler_name: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            component="api",
            **kwargs
        )
        self.path = path
        self.method = method
        self.handler_name = handler_name
