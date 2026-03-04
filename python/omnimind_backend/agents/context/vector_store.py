"""Vector store implementation for context retrieval.

Provides vector storage and search capabilities for
semantic context retrieval operations.
"""

from __future__ import annotations

import asyncio
import numpy as np
from typing import Any, Dict, List, Optional
from uuid import uuid4

from omnimind_backend.agents.core.interfaces import VectorStore
from omnimind_backend.agents.core.exceptions import VectorStoreError
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class InMemoryVectorStore(VectorStore):
    """In-memory vector store implementation for development/testing."""
    
    def __init__(self, vector_size: int = 256):
        self.vector_size = vector_size
        self.collections: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def search_session_context(
        self,
        session_id: str,
        query_vector: List[float],
        limit: int,
        score_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in session context."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    return []
                
                collection = self.collections[session_id]
                vectors = collection.get("vectors", [])
                
                if not vectors:
                    return []
                
                # Calculate cosine similarity
                similarities = []
                query_np = np.array(query_vector)
                
                for vector_data in vectors:
                    stored_np = np.array(vector_data["vector"])
                    
                    # Cosine similarity
                    similarity = np.dot(query_np, stored_np) / (
                        np.linalg.norm(query_np) * np.linalg.norm(stored_np)
                    )
                    
                    if similarity >= score_threshold:
                        similarities.append({
                            "id": vector_data["id"],
                            "similarity": float(similarity),
                            "metadata": vector_data.get("metadata", {}),
                            "content": vector_data.get("content", ""),
                        })
                
                # Sort by similarity and limit results
                similarities.sort(key=lambda x: x["similarity"], reverse=True)
                return similarities[:limit]
        
        except Exception as e:
            _logger.error("vector_search_failed", session_id=session_id, error=str(e))
            raise VectorStoreError(
                f"Vector search failed: {e}",
                operation="search",
                session_id=session_id
            )
    
    async def create_session_collection(self, session_id: str) -> None:
        """Create collection for session vectors."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    self.collections[session_id] = {
                        "vectors": [],
                        "created_at": asyncio.get_event_loop().time(),
                    }
                    _logger.info("session_collection_created", session_id=session_id)
        except Exception as e:
            _logger.error("collection_creation_failed", session_id=session_id, error=str(e))
            raise VectorStoreError(
                f"Collection creation failed: {e}",
                operation="create_collection",
                session_id=session_id
            )
    
    async def store_vectors(
        self,
        session_id: str,
        vectors: List[Dict[str, Any]],
    ) -> None:
        """Store vectors with metadata."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    await self.create_session_collection(session_id)
                
                collection = self.collections[session_id]
                
                for vector_data in vectors:
                    # Validate vector size
                    vector = vector_data.get("vector", [])
                    if len(vector) != self.vector_size:
                        raise VectorStoreError(
                            f"Vector size mismatch: expected {self.vector_size}, got {len(vector)}"
                        )
                    
                    # Add unique ID if not present
                    if "id" not in vector_data:
                        vector_data["id"] = str(uuid4())
                    
                    # Add timestamp
                    vector_data["stored_at"] = asyncio.get_event_loop().time()
                    
                    collection["vectors"].append(vector_data)
                
                _logger.info(
                    "vectors_stored",
                    session_id=session_id,
                    count=len(vectors),
                    total_vectors=len(collection["vectors"])
                )
        
        except Exception as e:
            _logger.error("vector_storage_failed", session_id=session_id, error=str(e))
            raise VectorStoreError(
                f"Vector storage failed: {e}",
                operation="store",
                session_id=session_id
            )
    
    async def get_collection_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session collection."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    return {"exists": False}
                
                collection = self.collections[session_id]
                vectors = collection.get("vectors", [])
                
                return {
                    "exists": True,
                    "vector_count": len(vectors),
                    "created_at": collection.get("created_at"),
                    "last_updated": max(
                        (v.get("stored_at", 0) for v in vectors), default=0
                    ),
                }
        
        except Exception as e:
            _logger.error("collection_stats_failed", session_id=session_id, error=str(e))
            raise VectorStoreError(
                f"Failed to get collection stats: {e}",
                operation="stats",
                session_id=session_id
            )
    
    async def delete_collection(self, session_id: str) -> None:
        """Delete a session collection."""
        try:
            async with self._lock:
                if session_id in self.collections:
                    del self.collections[session_id]
                    _logger.info("collection_deleted", session_id=session_id)
        except Exception as e:
            _logger.error("collection_deletion_failed", session_id=session_id, error=str(e))
            raise VectorStoreError(
                f"Collection deletion failed: {e}",
                operation="delete_collection",
                session_id=session_id
            )


class EmbeddingProvider:
    """Simple embedding provider for generating vectors."""
    
    def __init__(self, vector_size: int = 256):
        self.vector_size = vector_size
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text.
        
        This is a placeholder implementation that generates
        random vectors. In production, this would use
        a proper embedding model.
        """
        # TODO: Replace with actual embedding model
        import random
        random.seed(hash(text) % (2**32))  # Reproducible for same text
        return [random.uniform(-1, 1) for _ in range(self.vector_size)]
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.generate_embedding(text) for text in texts]


# Global vector store instance
_vector_store: VectorStore | None = None
_embedding_provider: EmbeddingProvider | None = None


async def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = InMemoryVectorStore()
    return _vector_store


def get_embedding_provider() -> EmbeddingProvider:
    """Get the global embedding provider instance."""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = EmbeddingProvider()
    return _embedding_provider
