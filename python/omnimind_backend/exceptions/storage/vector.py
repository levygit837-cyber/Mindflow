"""Vector store exceptions.

Exceptions for vector database operations, embedding failures,
and similarity search errors.
"""

from __future__ import annotations

from omnimind_backend.exceptions.base.core import InfrastructureError


class VectorStoreError(InfrastructureError):
    """Vector store operation failure."""
    
    def __init__(
        self,
        message: str,
        *,
        vector_store: str | None = None,
        index_name: str | None = None,
        operation: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            service="vector_store",
            operation=operation,
            component="storage",
            **kwargs
        )
        self.vector_store = vector_store
        self.index_name = index_name
