"""Context management interfaces for MindFlow agents.

Defines contracts for context retrieval, vector storage,
and caching operations.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.session.contracts import RetrievedContext


@runtime_checkable
class ContextRetriever(Protocol):
    """Contract for context retrieval implementations."""
    
    async def get_relevant_context(
        self,
        agent_id: str,
        query: str,
        session_id: str,
        context_window: tuple[int, int] = (0, 100000),
        include_related: bool = True,
        max_results: int = 5,
    ) -> RetrievedContext:
        """Retrieve relevant context for an agent."""
        ...

    async def get_context_window(
        self,
        session_id: str,
        token_range: tuple[int, int],
        include_related: bool = False,
    ) -> RetrievedContext:
        """Get context from specific token window."""
        ...

    async def get_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[RetrievedContext]:
        """Get context using semantic search."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Contract for vector storage implementations."""
    
    async def search_session_context(
        self,
        session_id: str,
        query_vector: list[float],
        limit: int,
        score_threshold: float,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in session context."""
        ...

    async def create_session_collection(self, session_id: str) -> None:
        """Create collection for session vectors."""
        ...

    async def store_vectors(
        self,
        session_id: str,
        vectors: list[dict[str, Any]],
    ) -> None:
        """Store vectors with metadata."""
        ...


@runtime_checkable
class Cache(Protocol):
    """Generic cache contract."""
    
    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        ...

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ...

    def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...

    def clear(self) -> None:
        """Clear all cache entries."""
        ...
