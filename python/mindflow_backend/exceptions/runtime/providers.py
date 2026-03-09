"""LLM provider exceptions.

Exceptions for LLM provider failures, API errors,
and model availability issues.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_new import NetworkError


class ProviderError(NetworkError):
    """LLM provider failure."""
    
    def __init__(
        self,
        message: str,
        *,
        provider_name: str | None = None,
        model_name: str | None = None,
        endpoint: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            endpoint=endpoint,
            component="runtime",
            **kwargs
        )
        self.provider_name = provider_name
        self.model_name = model_name
