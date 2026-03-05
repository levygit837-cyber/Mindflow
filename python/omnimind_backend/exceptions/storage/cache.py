"""Cache operation exceptions.

Exceptions for cache operations, Redis failures,
and caching strategy errors.
"""

from __future__ import annotations

from omnimind_backend.exceptions.base.core import InfrastructureError


class CacheError(InfrastructureError):
    """Cache operation failure."""
    
    def __init__(
        self,
        message: str,
        *,
        cache_backend: str | None = None,
        cache_key: str | None = None,
        operation: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            service="cache",
            operation=operation,
            component="storage",
            **kwargs
        )
        self.cache_backend = cache_backend
        self.cache_key = cache_key
