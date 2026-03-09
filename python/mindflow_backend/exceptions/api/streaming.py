"""API streaming exceptions.

Exceptions for streaming failures, connection issues,
and real-time communication errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_new import NetworkError


class StreamingError(NetworkError):
    """API streaming failure."""
    
    def __init__(
        self,
        message: str,
        *,
        stream_type: str | None = None,
        connection_id: str | None = None,
        client_disconnected: bool = False,
        **kwargs,
    ):
        super().__init__(
            message,
            component="api",
            **kwargs
        )
        self.stream_type = stream_type
        self.connection_id = connection_id
        self.client_disconnected = client_disconnected
