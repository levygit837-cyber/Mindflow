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
    
    async def search_by_topic(
        self,
        query: str,
        session_id: str,
        topic_filters: list[str] | None = None
    ) -> dict[str, Any]:
        """Search context by topic."""
        ...
    
    async def search_semantic(
        self,
        query: str,
        session_id: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> dict[str, Any]:
        """Search context semantically."""
        ...
    
    async def get_context_summary(
        self,
        session_id: str,
        context_window: tuple[int, int]
    ) -> dict[str, Any]:
        """Get context summary."""
        ...
    
    async def update_context_index(
        self,
        session_id: str,
        new_content: str
    ) -> dict[str, Any]:
        """Update context search index."""
        ...


@runtime_checkable
class EmbeddingServiceInterface(Protocol):
    """Interface for embedding generation operations."""
    
    async def generate_embedding(
        self,
        text: str,
        model: str | None = None,
        language: str | None = None
    ) -> list[float]:
        """Generate embedding for text."""
        ...
    
    async def generate_batch_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
        batch_size: int = 32
    ) -> list[list[float]]:
        """Generate embeddings for batch of texts."""
        ...
    
    async def get_embedding_model_info(self, model: str) -> dict[str, Any]:
        """Get embedding model information."""
        ...
    
    async def compare_embeddings(
        self,
        embedding1: list[float],
        embedding2: list[float]
    ) -> float:
        """Compare two embeddings and return similarity score."""
        ...
    
    async def detect_language(self, text: str) -> str:
        """Detect language of text."""
        ...
    
    async def get_supported_languages(self) -> list[str]:
        """Get supported languages for multilingual embeddings."""
        ...
    
    async def optimize_embedding_for_task(
        self,
        embedding: list[float],
        task_type: str
    ) -> list[float]:
        """Optimize embedding for specific task type."""
        ...


@runtime_checkable
class VectorServiceInterface(Protocol):
    """Interface for vector database operations."""
    
    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        distance_metric: str = "cosine"
    ) -> dict[str, Any]:
        """Create vector collection."""
        ...
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]]
    ) -> list[str]:
        """Insert vectors into collection."""
        ...
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        ...
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str]
    ) -> dict[str, Any]:
        """Delete vectors by ID."""
        ...
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Update vector and metadata."""
        ...
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str
    ) -> dict[str, Any] | None:
        """Get vector by ID."""
        ...
    
    async def list_collections(self) -> list[dict[str, Any]]:
        """List all collections."""
        ...
    
    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics."""
        ...
    
    async def optimize_index(self, collection_name: str) -> dict[str, Any]:
        """Optimize vector index for performance."""
        ...
