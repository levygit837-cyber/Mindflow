"""Vector database abstraction layer.

Provides a unified interface for different vector database backends
(pgvector, qdrant, chroma) with automatic fallback and migration support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal
from uuid import UUID

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector database connection."""
        pass
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a new vector collection."""
        pass
    
    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into a collection.
        
        Args:
            collection_name: Name of the collection
            vectors: List of vectors with metadata
            
        Returns:
            List of vector IDs
        """
        pass
    
    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_dict: Optional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        pass
    
    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors by ID."""
        pass
    
    @abstractmethod
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get a specific vector by ID."""
        pass
    
    @abstractmethod
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update a vector and its metadata."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass


class PgVectorDatabase(VectorDatabase):
    """PostgreSQL pgvector implementation."""
    
    def __init__(self, connection_string: str, dimensions: int = 256) -> None:
        """Initialize pgvector database.
        
        Args:
            connection_string: PostgreSQL connection string
            dimensions: Vector dimensions
        """
        self.connection_string = connection_string
        self.dimensions = dimensions
        self._connection = None
    
    async def initialize(self) -> None:
        """Initialize pgvector connection and extension."""
        try:
            # TODO: Implement actual pgvector connection
            _logger.info("pgvector_initialized", dimensions=self.dimensions)
        except Exception as e:
            _logger.error("pgvector_initialization_failed", error=str(e))
            raise
    
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a pgvector table for the collection."""
        # TODO: Implement actual table creation with pgvector extension
        _logger.info("pgvector_collection_created", name=name, dimension=dimension)
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into pgvector table."""
        # TODO: Implement actual vector insertion
        vector_ids = [str(UUID()) for _ in vectors]
        _logger.info(
            "pgvector_vectors_inserted",
            collection_name=collection_name,
            count=len(vectors),
        )
        return vector_ids
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors using pgvector similarity."""
        # TODO: Implement actual vector search with cosine similarity
        results = []
        _logger.info(
            "pgvector_search_completed",
            collection_name=collection_name,
            limit=limit,
            score_threshold=score_threshold,
            results_count=len(results),
        )
        return results
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors from pgvector table."""
        # TODO: Implement actual vector deletion
        _logger.info(
            "pgvector_vectors_deleted",
            collection_name=collection_name,
            count=len(vector_ids),
        )
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get vector from pgvector table."""
        # TODO: Implement actual vector retrieval
        return None
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update vector in pgvector table."""
        # TODO: Implement actual vector update
        _logger.info(
            "pgvector_vector_updated",
            collection_name=collection_name,
            vector_id=vector_id,
        )
    
    async def close(self) -> None:
        """Close pgvector connection."""
        if self._connection:
            # TODO: Implement actual connection closing
            _logger.info("pgvector_connection_closed")


class QdrantDatabase(VectorDatabase):
    """Qdrant vector database implementation."""
    
    def __init__(self, url: str, api_key: str | None = None, dimensions: int = 256) -> None:
        """Initialize Qdrant database.
        
        Args:
            url: Qdrant server URL
            api_key: Optional API key
            dimensions: Vector dimensions
        """
        self.url = url
        self.api_key = api_key
        self.dimensions = dimensions
        self._client = None
    
    async def initialize(self) -> None:
        """Initialize Qdrant client."""
        try:
            # TODO: Implement actual Qdrant client initialization
            _logger.info("qdrant_initialized", url=self.url, dimensions=self.dimensions)
        except Exception as e:
            _logger.error("qdrant_initialization_failed", error=str(e))
            raise
    
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a Qdrant collection."""
        # TODO: Implement actual collection creation
        _logger.info("qdrant_collection_created", name=name, dimension=dimension)
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into Qdrant collection."""
        # TODO: Implement actual vector insertion
        vector_ids = [str(UUID()) for _ in vectors]
        _logger.info(
            "qdrant_vectors_inserted",
            collection_name=collection_name,
            count=len(vectors),
        )
        return vector_ids
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors using Qdrant."""
        # TODO: Implement actual vector search
        results = []
        _logger.info(
            "qdrant_search_completed",
            collection_name=collection_name,
            limit=limit,
            score_threshold=score_threshold,
            results_count=len(results),
        )
        return results
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors from Qdrant collection."""
        # TODO: Implement actual vector deletion
        _logger.info(
            "qdrant_vectors_deleted",
            collection_name=collection_name,
            count=len(vector_ids),
        )
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get vector from Qdrant collection."""
        # TODO: Implement actual vector retrieval
        return None
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update vector in Qdrant collection."""
        # TODO: Implement actual vector update
        _logger.info(
            "qdrant_vector_updated",
            collection_name=collection_name,
            vector_id=vector_id,
        )
    
    async def close(self) -> None:
        """Close Qdrant client."""
        if self._client:
            # TODO: Implement actual client closing
            _logger.info("qdrant_client_closed")


class ChromaDatabase(VectorDatabase):
    """Chroma vector database implementation."""
    
    def __init__(self, path: str | None = None, dimensions: int = 256) -> None:
        """Initialize Chroma database.
        
        Args:
            path: Chroma database path (None for in-memory)
            dimensions: Vector dimensions
        """
        self.path = path
        self.dimensions = dimensions
        self._client = None
    
    async def initialize(self) -> None:
        """Initialize Chroma client."""
        try:
            # TODO: Implement actual Chroma client initialization
            _logger.info("chroma_initialized", path=self.path, dimensions=self.dimensions)
        except Exception as e:
            _logger.error("chroma_initialization_failed", error=str(e))
            raise
    
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a Chroma collection."""
        # TODO: Implement actual collection creation
        _logger.info("chroma_collection_created", name=name, dimension=dimension)
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into Chroma collection."""
        # TODO: Implement actual vector insertion
        vector_ids = [str(UUID()) for _ in vectors]
        _logger.info(
            "chroma_vectors_inserted",
            collection_name=collection_name,
            count=len(vectors),
        )
        return vector_ids
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors using Chroma."""
        # TODO: Implement actual vector search
        results = []
        _logger.info(
            "chroma_search_completed",
            collection_name=collection_name,
            limit=limit,
            score_threshold=score_threshold,
            results_count=len(results),
        )
        return results
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors from Chroma collection."""
        # TODO: Implement actual vector deletion
        _logger.info(
            "chroma_vectors_deleted",
            collection_name=collection_name,
            count=len(vector_ids),
        )
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get vector from Chroma collection."""
        # TODO: Implement actual vector retrieval
        return None
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update vector in Chroma collection."""
        # TODO: Implement actual vector update
        _logger.info(
            "chroma_vector_updated",
            collection_name=collection_name,
            vector_id=vector_id,
        )
    
    async def close(self) -> None:
        """Close Chroma client."""
        if self._client:
            # TODO: Implement actual client closing
            _logger.info("chroma_client_closed")


class VectorManager:
    """Vector database manager with provider abstraction."""
    
    def __init__(self) -> None:
        """Initialize vector manager."""
        self._db: VectorDatabase | None = None
        self._provider: Literal["pgvector", "qdrant", "chroma"] | None = None
    
    async def initialize(self) -> None:
        """Initialize the vector database based on configuration."""
        settings = get_settings()
        
        self._provider = settings.vector_db_provider
        
        if self._provider == "pgvector":
            self._db = PgVectorDatabase(
                connection_string=settings.database_url,
                dimensions=settings.vector_db_dimensions,
            )
        elif self._provider == "qdrant":
            if not settings.vector_db_url:
                raise ValueError("QDRANT_URL required when using qdrant provider")
            self._db = QdrantDatabase(
                url=settings.vector_db_url,
                api_key=settings.vector_db_api_key,
                dimensions=settings.vector_db_dimensions,
            )
        elif self._provider == "chroma":
            self._db = ChromaDatabase(
                path=settings.vector_db_url,  # Use URL as path for Chroma
                dimensions=settings.vector_db_dimensions,
            )
        else:
            raise ValueError(f"Unsupported vector database provider: {self._provider}")
        
        await self._db.initialize()
        _logger.info("vector_manager_initialized", provider=self._provider)
    
    async def create_session_collection(self, session_id: str) -> None:
        """Create a collection for a specific session."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"session_{session_id}"
        await self._db.create_collection(collection_name, self._db.dimensions)
        _logger.info("session_collection_created", session_id=session_id)
    
    async def store_session_embeddings(
        self,
        session_id: str,
        embeddings: list[dict[str, Any]],
    ) -> list[str]:
        """Store embeddings for a session."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"session_{session_id}"
        vector_ids = await self._db.insert_vectors(collection_name, embeddings)
        _logger.info(
            "session_embeddings_stored",
            session_id=session_id,
            count=len(embeddings),
        )
        return vector_ids
    
    async def search_session_context(
        self,
        session_id: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search for context within a session."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"session_{session_id}"
        results = await self._db.search_vectors(
            collection_name, query_vector, limit, score_threshold
        )
        _logger.info(
            "session_context_searched",
            session_id=session_id,
            limit=limit,
            results_count=len(results),
        )
        return results
    
    async def create_dt_collection(self, component_id: str, component_type: str = "component") -> None:
        """Create a collection for a DT component or sub-component."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"dt_{component_type}_{component_id}"
        await self._db.create_collection(collection_name, self._db.dimensions)
        _logger.info(
            "dt_collection_created", 
            component_id=component_id, 
            component_type=component_type
        )
    
    async def update_component_context(
        self,
        component_id: str,
        context_data: dict[str, Any],
        component_type: str = "component",
    ) -> str:
        """Update or insert context for a specific component."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"dt_{component_type}_{component_id}"
        
        # Prepare vector with metadata
        vector_data = {
            "id": str(UUID()),
            "vector": context_data.get("vector", []),
            "metadata": {
                "component_id": component_id,
                "component_type": component_type,
                "state": context_data.get("state", "unknown"),
                "timestamp": context_data.get("timestamp", ""),
                "content": context_data.get("content", ""),
                "dependencies": context_data.get("dependencies", []),
                "artifacts": context_data.get("artifacts", []),
            }
        }
        
        # Check if vector already exists for this component
        existing_vectors = await self._db.search_vectors(
            collection_name, 
            context_data.get("vector", []), 
            limit=1,
            filter_dict={"component_id": component_id}
        )
        
        if existing_vectors:
            # Update existing vector
            await self._db.update_vector(
                collection_name, 
                existing_vectors[0]["id"], 
                context_data.get("vector", []),
                vector_data["metadata"]
            )
            vector_id = existing_vectors[0]["id"]
        else:
            # Insert new vector
            vector_ids = await self._db.insert_vectors(collection_name, [vector_data])
            vector_id = vector_ids[0]
        
        _logger.info(
            "component_context_updated",
            component_id=component_id,
            component_type=component_type,
            vector_id=vector_id,
        )
        return vector_id
    
    async def cross_component_search(
        self,
        query_component_id: str,
        query_vector: list[float],
        component_types: list[str] | None = None,
        exclude_component_id: str | None = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search across all DT component collections for semantic matches."""
        if not self._db:
            await self.initialize()
        
        if component_types is None:
            component_types = ["component", "sub_component"]
        
        all_results = []
        
        for component_type in component_types:
            # Search in collections of this type
            collection_pattern = f"dt_{component_type}_"
            
            # This would require listing collections - for now, we'll search
            # in a way that assumes we can filter by collection pattern
            filter_dict = {}
            if exclude_component_id:
                filter_dict["component_id"] = {"$ne": exclude_component_id}
            
            # Note: This is a simplified implementation
            # In practice, you'd need to iterate over actual collections
            results = await self._db.search_vectors(
                f"dt_{component_type}_*",  # This would need proper pattern matching
                query_vector,
                limit,
                score_threshold,
                filter_dict
            )
            
            # Add component type info to results
            for result in results:
                result["component_type"] = component_type
            
            all_results.extend(results)
        
        # Sort by score and return top results
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        final_results = all_results[:limit]
        
        _logger.info(
            "cross_component_search_completed",
            query_component_id=query_component_id,
            component_types=component_types,
            results_count=len(final_results),
        )
        
        return final_results
    
    async def close(self) -> None:
        """Close the vector database connection."""
        if self._db:
            await self._db.close()
            _logger.info("vector_manager_closed", provider=self._provider)


# Global vector manager instance
_vector_manager: VectorManager | None = None


async def get_vector_manager() -> VectorManager:
    """Get the global vector manager instance."""
    global _vector_manager
    if _vector_manager is None:
        _vector_manager = VectorManager()
        await _vector_manager.initialize()
    return _vector_manager
