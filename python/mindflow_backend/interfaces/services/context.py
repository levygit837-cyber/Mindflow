"""Context service interfaces for MindFlow backend.

This module defines interfaces for semantic context retrieval,
embedding generation, and vector database management.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class RetrievalServiceInterface(Protocol):
    """Interface for context retrieval operations."""
    
    async def retrieve_context(
        self,
        query: str,
        session_id: str,
        retrieval_mode: str = "semantic",
        limit: int = 10
    ) -> dict[str, Any]:
        """Retrieve context for query."""
        ...
    
    async def search_by_range(
        self,
        session_id: str,
        token_range: tuple[int, int]
    ) -> dict[str, Any]:
        """Search context by token range."""
        ...
    
    async def get_context_window(
        self,
        session_id: str,
        window_size: int = 4000
    ) -> dict[str, Any]:
        """Get current context window."""
        ...
    
    async def update_context(
        self,
        session_id: str,
        context_data: dict[str, Any]
    ) -> bool:
        """Update context with new data."""
        ...


@runtime_checkable
class EmbeddingServiceInterface(Protocol):
    """Interface for embedding generation operations."""
    
    async def generate_embedding(
        self,
        text: str,
        model: str = "default"
    ) -> list[float]:
        """Generate embedding for text."""
        ...
    
    async def batch_generate_embeddings(
        self,
        texts: list[str],
        model: str = "default"
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...
    
    async def compare_embeddings(
        self,
        embedding1: list[float],
        embedding2: list[float]
    ) -> float:
        """Compare similarity between embeddings."""
        ...


@runtime_checkable
class VectorStoreInterface(Protocol):
    """Interface for vector database operations."""
    
    async def store_vector(
        self,
        vector_id: str,
        embedding: list[float],
        metadata: dict[str, Any]
    ) -> bool:
        """Store vector in database."""
        ...
    
    async def search_vectors(
        self,
        query_embedding: list[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """Search similar vectors."""
        ...
    
    async def delete_vector(
        self,
        vector_id: str
    ) -> bool:
        """Delete vector from database."""
        ...
