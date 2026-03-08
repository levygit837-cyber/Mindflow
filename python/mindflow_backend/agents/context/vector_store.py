"""Vector store implementation for context retrieval.

Provides vector storage and search capabilities for
semantic context retrieval operations.
"""

from __future__ import annotations

import asyncio
import numpy as np
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mindflow_backend.agents.core.interfaces import VectorStore
from mindflow_backend.exceptions import AgentVectorStoreError
from mindflow_backend.infra.logging import get_logger

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
            raise AgentVectorStoreError(
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
            raise AgentVectorStoreError(
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
                        raise AgentVectorStoreError(
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
            raise AgentVectorStoreError(
                f"Vector storage failed: {e}",
                operation="store",
                session_id=session_id
            )
    
    async def search_subtask_context(
        self,
        session_id: str,
        task_id: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        include_dependencies: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for context relevant to specific sub-task."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    return []
                
                collection = self.collections[session_id]
                vectors = collection.get("vectors", [])
                
                if not vectors:
                    return []
                
                # Filter vectors relevant to the task
                relevant_vectors = []
                for vector_data in vectors:
                    metadata = vector_data.get("metadata", {})
                    
                    # Include if it's from the same task, a dependency, or general context
                    vector_task_id = metadata.get("task_id")
                    if (vector_task_id == task_id or 
                        (include_dependencies and metadata.get("is_dependency", False)) or
                        not vector_task_id):  # General context
                        relevant_vectors.append(vector_data)
                
                # Calculate similarities
                similarities = []
                query_np = np.array(query_vector)
                
                for vector_data in relevant_vectors:
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
                            "task_id": vector_data.get("metadata", {}).get("task_id"),
                            "agent_type": vector_data.get("metadata", {}).get("agent_type"),
                        })
                
                # Sort by similarity and limit results
                similarities.sort(key=lambda x: x["similarity"], reverse=True)
                return similarities[:limit]
        
        except Exception as e:
            _logger.error("subtask_search_failed", session_id=session_id, task_id=task_id, error=str(e))
            raise AgentVectorStoreError(
                f"Subtask search failed: {e}",
                operation="search_subtask",
                session_id=session_id
            )
    
    async def store_subtask_context(
        self,
        session_id: str,
        task_id: str,
        agent_type: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any] | None = None,
        dependencies: List[str] | None = None,
    ) -> str:
        """Store context for a specific sub-task with dependencies."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    await self.create_session_collection(session_id)
                
                collection = self.collections[session_id]
                
                # Prepare metadata
                vector_metadata = {
                    "task_id": task_id,
                    "agent_type": agent_type,
                    "content_type": "subtask_context",
                    "dependencies": dependencies or [],
                    "created_at": asyncio.get_event_loop().time(),
                    **(metadata or {})
                }
                
                # Create vector data
                vector_data = {
                    "id": str(uuid4()),
                    "vector": embedding,
                    "content": content,
                    "metadata": vector_metadata,
                    "stored_at": asyncio.get_event_loop().time(),
                }
                
                collection["vectors"].append(vector_data)
                
                _logger.info(
                    "subtask_context_stored",
                    session_id=session_id,
                    task_id=task_id,
                    agent_type=agent_type,
                    vector_id=vector_data["id"]
                )
                
                return vector_data["id"]
        
        except Exception as e:
            _logger.error("subtask_storage_failed", session_id=session_id, task_id=task_id, error=str(e))
            raise AgentVectorStoreError(
                f"Subtask storage failed: {e}",
                operation="store_subtask",
                session_id=session_id
            )
    
    async def get_task_dependencies_context(
        self,
        session_id: str,
        task_id: str,
        dependency_task_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Get context from specific dependency tasks."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    return []
                
                collection = self.collections[session_id]
                vectors = collection.get("vectors", [])
                
                # Filter vectors from dependency tasks
                dependency_contexts = []
                for vector_data in vectors:
                    metadata = vector_data.get("metadata", {})
                    vector_task_id = metadata.get("task_id")
                    
                    if vector_task_id in dependency_task_ids:
                        dependency_contexts.append({
                            "id": vector_data["id"],
                            "content": vector_data.get("content", ""),
                            "metadata": metadata,
                            "task_id": vector_task_id,
                            "agent_type": metadata.get("agent_type"),
                            "stored_at": vector_data.get("stored_at"),
                        })
                
                # Sort by stored_at (most recent first)
                dependency_contexts.sort(key=lambda x: x.get("stored_at", 0), reverse=True)
                return dependency_contexts
        
        except Exception as e:
            _logger.error("dependencies_context_failed", session_id=session_id, task_id=task_id, error=str(e))
            raise AgentVectorStoreError(
                f"Dependencies context failed: {e}",
                operation="get_dependencies",
                session_id=session_id
            )
    
    async def update_task_status(
        self,
        session_id: str,
        task_id: str,
        status: str,
        completion_data: Dict[str, Any] | None = None,
    ) -> None:
        """Update the status of a task in the vector store."""
        try:
            async with self._lock:
                if session_id not in self.collections:
                    return
                
                collection = self.collections[session_id]
                vectors = collection.get("vectors", [])
                
                # Update status for all vectors from this task
                updated_count = 0
                for vector_data in vectors:
                    metadata = vector_data.get("metadata", {})
                    if metadata.get("task_id") == task_id:
                        metadata["task_status"] = status
                        metadata["status_updated_at"] = asyncio.get_event_loop().time()
                        if completion_data:
                            metadata["completion_data"] = completion_data
                        updated_count += 1
                
                _logger.info(
                    "task_status_updated",
                    session_id=session_id,
                    task_id=task_id,
                    status=status,
                    updated_vectors=updated_count
                )
        
        except Exception as e:
            _logger.error("task_status_update_failed", session_id=session_id, task_id=task_id, error=str(e))
            raise AgentVectorStoreError(
                f"Task status update failed: {e}",
                operation="update_status",
                session_id=session_id
            )
    
    async def wait_for_task_context(
        self,
        session_id: str,
        task_id: str,
        required_task_ids: List[str],
        timeout_seconds: int = 30,
        poll_interval: float = 0.5,
    ) -> Dict[str, Any]:
        """Wait for required task contexts to become available."""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check if all required tasks have context
                dependency_contexts = await self.get_task_dependencies_context(
                    session_id, task_id, required_task_ids
                )
                
                # Check if we have context for all required tasks
                available_tasks = {ctx["task_id"] for ctx in dependency_contexts}
                missing_tasks = set(required_task_ids) - available_tasks
                
                if not missing_tasks:
                    return {
                        "status": "ready",
                        "contexts": dependency_contexts,
                        "wait_time": time.time() - start_time,
                    }
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                _logger.warning("context_wait_error", task_id=task_id, error=str(e))
                await asyncio.sleep(poll_interval)
        
        # Timeout reached
        return {
            "status": "timeout",
            "missing_tasks": list(missing_tasks),
            "available_contexts": dependency_contexts,
            "wait_time": timeout_seconds,
        }
    
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
            raise AgentVectorStoreError(
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
            raise AgentVectorStoreError(
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
