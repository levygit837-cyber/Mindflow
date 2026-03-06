"""Network connectivity exceptions.

Exceptions for network failures, DNS resolution,
and connectivity issues.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core import NetworkError as BaseNetworkError


class NetworkError(BaseNetworkError):
    """External network connectivity failure."""
    
    def __init__(
        self,
        message: str,
        *,
        host: str | None = None,
        port: int | None = None,
        protocol: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            endpoint=f"{protocol}://{host}:{port}" if host and port else None,
            component="external",
            **kwargs
        )
        self.host = host
        self.port = port
        self.protocol = protocol
