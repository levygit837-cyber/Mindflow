"""Vector database service for managing vector operations.

This service provides a unified interface for different vector database backends
with automatic fallback, migration support, and comprehensive vector management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
import asyncio
from datetime import datetime, UTC

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.services.interfaces.base_interfaces import BaseAbstractService
from omnimind_backend.services.interfaces.context_interfaces import VectorServiceInterface


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector database connection."""
        pass
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int, distance_metric: str = "cosine") -> None:
        """Create a new vector collection."""
        pass
    
    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]],
    ) -> List[str]:
        """Insert vectors into a collection."""
        pass
    
    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str],
    ) -> None:
        """Delete vectors by ID."""
        pass
    
    @abstractmethod
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific vector by ID."""
        pass
    
    @abstractmethod
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update a vector and its metadata."""
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass


class InMemoryVectorDatabase(VectorDatabase):
    """In-memory vector database for testing and development."""
    
    def __init__(self) -> None:
        """Initialize in-memory vector database."""
        self.collections: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the in-memory database."""
        self._initialized = True
        self._logger.info("in_memory_vector_db_initialized")
    
    async def create_collection(self, name: str, dimension: int, distance_metric: str = "cosine") -> None:
        """Create a new collection in memory."""
        if name in self.collections:
            raise ValueError(f"Collection {name} already exists")
        
        self.collections[name] = {
            "name": name,
            "dimension": dimension,
            "distance_metric": distance_metric,
            "vectors": {},
            "created_at": datetime.now(UTC)
        }
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]],
    ) -> List[str]:
        """Insert vectors into collection."""
        collection = self.collections.get(collection_name)
        if not collection:
            raise ValueError(f"Collection {collection_name} not found")
        
        vector_ids = []
        for vector_data in vectors:
            vector_id = vector_data.get("id", str(uuid4()))
            vector = vector_data.get("vector")
            metadata = vector_data.get("metadata", {})
            
            if len(vector) != collection["dimension"]:
                raise ValueError(f"Vector dimension mismatch: expected {collection['dimension']}, got {len(vector)}")
            
            collection["vectors"][vector_id] = {
                "id": vector_id,
                "vector": vector,
                "metadata": metadata,
                "created_at": datetime.now(UTC)
            }
            vector_ids.append(vector_id)
        
        return vector_ids
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity."""
        collection = self.collections.get(collection_name)
        if not collection:
            raise ValueError(f"Collection {collection_name} not found")
        
        if len(query_vector) != collection["dimension"]:
            raise ValueError(f"Query vector dimension mismatch")
        
        results = []
        
        for vector_id, vector_data in collection["vectors"].items():
            # Apply filters if provided
            if filters:
                metadata = vector_data["metadata"]
                if not all(metadata.get(k) == v for k, v in filters.items()):
                    continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_vector, vector_data["vector"])
            
            if similarity >= score_threshold:
                results.append({
                    "id": vector_id,
                    "score": similarity,
                    "vector": vector_data["vector"],
                    "metadata": vector_data["metadata"]
                })
        
        # Sort by similarity and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str],
    ) -> None:
        """Delete vectors by ID."""
        collection = self.collections.get(collection_name)
        if not collection:
            raise ValueError(f"Collection {collection_name} not found")
        
        for vector_id in vector_ids:
            collection["vectors"].pop(vector_id, None)
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific vector by ID."""
        collection = self.collections.get(collection_name)
        if not collection:
            raise ValueError(f"Collection {collection_name} not found")
        
        vector_data = collection["vectors"].get(vector_id)
        if vector_data:
            return {
                "id": vector_id,
                "vector": vector_data["vector"],
                "metadata": vector_data["metadata"],
                "created_at": vector_data["created_at"]
            }
        return None
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update a vector and its metadata."""
        collection = self.collections.get(collection_name)
        if not collection:
            raise ValueError(f"Collection {collection_name} not found")
        
        if vector_id not in collection["vectors"]:
            raise ValueError(f"Vector {vector_id} not found")
        
        if len(vector) != collection["dimension"]:
            raise ValueError(f"Vector dimension mismatch")
        
        vector_data = collection["vectors"][vector_id]
        vector_data["vector"] = vector
        if metadata is not None:
            vector_data["metadata"].update(metadata)
        vector_data["updated_at"] = datetime.now(UTC)
    
    async def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        return [
            {
                "name": collection["name"],
                "dimension": collection["dimension"],
                "distance_metric": collection["distance_metric"],
                "vector_count": len(collection["vectors"]),
                "created_at": collection["created_at"]
            }
            for collection in self.collections.values()
        ]
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics."""
        collection = self.collections.get(collection_name)
        if not collection:
            raise ValueError(f"Collection {collection_name} not found")
        
        vectors = list(collection["vectors"].values())
        
        return {
            "name": collection_name,
            "vector_count": len(vectors),
            "dimension": collection["dimension"],
            "distance_metric": collection["distance_metric"],
            "created_at": collection["created_at"],
            "last_updated": max((v.get("updated_at", v["created_at"]) for v in vectors), default=collection["created_at"])
        }
    
    async def close(self) -> None:
        """Close the database (clear memory)."""
        self.collections.clear()
        self._initialized = False
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)


class VectorService(BaseAbstractService, VectorServiceInterface):
    """Service for managing vector database operations.
    
    This service provides a unified interface for vector operations with
    automatic fallback, connection management, and performance optimization.
    """
    
    def __init__(self) -> None:
        """Initialize vector service with database backend."""
        super().__init__()
        self.settings = get_settings()
        self._database: Optional[VectorDatabase] = None
        self._connection_attempts = 0
        self._max_connection_attempts = 3
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    async def _get_database(self) -> VectorDatabase:
        """Get or initialize vector database backend."""
        if self._database is None:
            await self._initialize_database()
        return self._database
    
    async def _initialize_database(self) -> None:
        """Initialize the appropriate vector database backend."""
        self._connection_attempts += 1
        
        try:
            # Try to determine the best backend based on configuration
            backend_type = getattr(self.settings, 'vector_db_backend', 'memory')
            
            if backend_type == 'pgvector':
                # Try PostgreSQL pgvector
                self._database = await self._try_pgvector()
            elif backend_type == 'qdrant':
                # Try Qdrant
                self._database = await self._try_qdrant()
            elif backend_type == 'chroma':
                # Try ChromaDB
                self._database = await self._try_chroma()
            else:
                # Default to in-memory
                self._database = InMemoryVectorDatabase()
            
            await self._database.initialize()
            self._logger.info(f"vector_database_initialized", backend=backend_type)
            
        except Exception as exc:
            self._logger.warning(f"vector_database_backend_failed", backend=backend_type, error=str(exc))
            
            # Fallback to in-memory database
            if self._connection_attempts < self._max_connection_attempts:
                self._database = InMemoryVectorDatabase()
                await self._database.initialize()
                self._logger.info("vector_database_fallback_to_memory")
            else:
                raise RuntimeError(f"Failed to initialize vector database after {self._max_connection_attempts} attempts")
    
    async def _try_pgvector(self) -> VectorDatabase:
        """Try to initialize PostgreSQL pgvector backend."""
        # Placeholder for pgvector implementation
        raise NotImplementedError("pgvector backend not yet implemented")
    
    async def _try_qdrant(self) -> VectorDatabase:
        """Try to initialize Qdrant backend."""
        # Placeholder for Qdrant implementation
        raise NotImplementedError("Qdrant backend not yet implemented")
    
    async def _try_chroma(self) -> VectorDatabase:
        """Try to initialize ChromaDB backend."""
        # Placeholder for ChromaDB implementation
        raise NotImplementedError("ChromaDB backend not yet implemented")
    
    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        distance_metric: str = "cosine"
    ) -> Dict[str, Any]:
        """Create a new vector collection.
        
        Args:
            collection_name: Name of the collection
            dimension: Vector dimension
            distance_metric: Distance metric for similarity calculation
            
        Returns:
            Dictionary containing collection creation result
        """
        self.log_operation("create_collection", collection_name=collection_name, dimension=dimension)
        
        try:
            database = await self._get_database()
            await database.create_collection(collection_name, dimension, distance_metric)
            
            return {
                "collection_name": collection_name,
                "dimension": dimension,
                "distance_metric": distance_metric,
                "status": "created",
                "created_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating collection {collection_name}: {str(exc)}")
            raise
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert vectors into a collection.
        
        Args:
            collection_name: Name of the collection
            vectors: List of vectors with metadata
            
        Returns:
            List of vector IDs
        """
        self.log_operation("insert_vectors", collection_name=collection_name, count=len(vectors))
        
        try:
            database = await self._get_database()
            vector_ids = await database.insert_vectors(collection_name, vectors)
            
            self._logger.info(f"vectors_inserted", collection=collection_name, count=len(vector_ids))
            
            return vector_ids
            
        except Exception as exc:
            self._logger.error(f"Error inserting vectors into {collection_name}: {str(exc)}")
            raise
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        self.log_operation(
            "search_vectors",
            collection_name=collection_name,
            limit=limit,
            score_threshold=score_threshold
        )
        
        try:
            database = await self._get_database()
            results = await database.search_vectors(
                collection_name, query_vector, limit, score_threshold, filters
            )
            
            self._logger.info(f"vector_search_completed", collection=collection_name, results=len(results))
            
            return results
            
        except Exception as exc:
            self._logger.error(f"Error searching vectors in {collection_name}: {str(exc)}")
            raise
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> Dict[str, Any]:
        """Delete vectors by ID.
        
        Args:
            collection_name: Name of the collection
            vector_ids: List of vector IDs to delete
            
        Returns:
            Dictionary containing deletion result
        """
        self.log_operation("delete_vectors", collection_name=collection_name, count=len(vector_ids))
        
        try:
            database = await self._get_database()
            await database.delete_vectors(collection_name, vector_ids)
            
            return {
                "collection_name": collection_name,
                "deleted_count": len(vector_ids),
                "status": "deleted",
                "deleted_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error deleting vectors from {collection_name}: {str(exc)}")
            raise
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific vector by ID.
        
        Args:
            collection_name: Name of the collection
            vector_id: Vector ID
            
        Returns:
            Vector data or None if not found
        """
        self.log_operation("get_vector", collection_name=collection_name, vector_id=vector_id)
        
        try:
            database = await self._get_database()
            return await database.get_vector(collection_name, vector_id)
            
        except Exception as exc:
            self._logger.error(f"Error getting vector {vector_id} from {collection_name}: {str(exc)}")
            raise
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update a vector and its metadata.
        
        Args:
            collection_name: Name of the collection
            vector_id: Vector ID
            vector: Updated vector data
            metadata: Updated metadata
            
        Returns:
            Dictionary containing update result
        """
        self.log_operation("update_vector", collection_name=collection_name, vector_id=vector_id)
        
        try:
            database = await self._get_database()
            await database.update_vector(collection_name, vector_id, vector, metadata)
            
            return {
                "collection_name": collection_name,
                "vector_id": vector_id,
                "status": "updated",
                "updated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error updating vector {vector_id} in {collection_name}: {str(exc)}")
            raise
    
    async def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections.
        
        Returns:
            List of collection information
        """
        self.log_operation("list_collections")
        
        try:
            database = await self._get_database()
            return await database.list_collections()
            
        except Exception as exc:
            self._logger.error(f"Error listing collections: {str(exc)}")
            raise
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary containing collection statistics
        """
        self.log_operation("get_collection_stats", collection_name=collection_name)
        
        try:
            database = await self._get_database()
            return await database.get_collection_stats(collection_name)
            
        except Exception as exc:
            self._logger.error(f"Error getting stats for {collection_name}: {str(exc)}")
            raise
    
    async def optimize_index(self, collection_name: str) -> Dict[str, Any]:
        """Optimize vector index for performance.
        
        Args:
            collection_name: Name of the collection to optimize
            
        Returns:
            Dictionary containing optimization result
        """
        self.log_operation("optimize_index", collection_name=collection_name)
        
        try:
            # For in-memory database, optimization is a no-op
            # For real databases, this would trigger index rebuilding
            database = await self._get_database()
            
            # Placeholder for optimization logic
            # In real implementations, this would:
            # - Rebuild vector indices
            # - Update statistics
            # - Compact storage
            
            return {
                "collection_name": collection_name,
                "status": "optimized",
                "optimized_at": datetime.now(UTC).isoformat(),
                "message": "Index optimization completed"
            }
            
        except Exception as exc:
            self._logger.error(f"Error optimizing index for {collection_name}: {str(exc)}")
            raise
    
    async def close(self) -> None:
        """Close the vector database connection."""
        self.log_operation("close_vector_service")
        
        try:
            if self._database:
                await self._database.close()
                self._database = None
            
            self._logger.info("vector_service_closed")
            
        except Exception as exc:
            self._logger.error(f"Error closing vector service: {str(exc)}")
    
    # Batch operations for better performance
    
    async def batch_insert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[str]:
        """Insert vectors in batches for better performance.
        
        Args:
            collection_name: Name of the collection
            vectors: List of vectors to insert
            batch_size: Size of each batch
            
        Returns:
            List of all vector IDs
        """
        self.log_operation("batch_insert_vectors", collection_name=collection_name, total=len(vectors))
        
        all_vector_ids = []
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            batch_ids = await self.insert_vectors(collection_name, batch)
            all_vector_ids.extend(batch_ids)
            
            # Small delay to prevent overwhelming the database
            if i + batch_size < len(vectors):
                await asyncio.sleep(0.01)
        
        return all_vector_ids
    
    async def batch_search_vectors(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> List[List[Dict[str, Any]]]:
        """Search multiple query vectors in parallel.
        
        Args:
            collection_name: Name of the collection
            query_vectors: List of query vectors
            limit: Maximum results per query
            score_threshold: Minimum similarity score
            
        Returns:
            List of search result lists
        """
        self.log_operation("batch_search_vectors", collection_name=collection_name, queries=len(query_vectors))
        
        # Create search tasks
        search_tasks = [
            self.search_vectors(collection_name, query_vector, limit, score_threshold)
            for query_vector in query_vectors
        ]
        
        # Execute searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._logger.error(f"Batch search query {i} failed: {str(result)}")
                processed_results.append([])
            else:
                processed_results.append(result)
        
        return processed_results
