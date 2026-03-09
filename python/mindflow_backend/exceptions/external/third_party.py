"""Third-party API exceptions.

Exceptions for external API failures, service errors,
and third-party integration issues.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_new import NetworkError


class ThirdPartyAPIError(NetworkError):
    """Third-party API failure."""
    
    def __init__(
        self,
        message: str,
        *,
        api_name: str | None = None,
        endpoint: str | None = None,
        status_code: int | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            service=api_name,
            component="external",
            **kwargs
        )
        self.api_name = api_name
        self.endpoint = endpoint
        self.status_code = status_code
