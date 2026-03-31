"""Vector store operations for memory embeddings."""

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.vector_manager import get_vector_manager

_logger = get_logger(__name__)


class VectorStore:
    """Vector store for memory embeddings."""
    
    def __init__(self, collection_prefix: str = "memory"):
        self.collection_prefix = collection_prefix
    
    async def store_embedding(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None
    ) -> str:
        """Store embedding in vector database."""
        try:
            vector_manager = await get_vector_manager()
            
            # Create collection for session if needed
            collection_name = f"{self.collection_prefix}_{agent_id}"
            await vector_manager.create_session_collection(session_id)
            
            # Store in vector database
            embedding_data = {
                "content": content,
                "vector": embedding,
                "metadata": metadata or {},
            }
            
            vector_ids = await vector_manager.store_session_embeddings(
                session_id=session_id,
                embeddings=[embedding_data],
            )
            
            return vector_ids[0] if vector_ids else ""
            
        except Exception as exc:
            _logger.error(f"Failed to store embedding: {str(exc)}")
            raise
    
    async def search_similar(
        self,
        session_id: str,
        agent_id: str,
        query_embedding: list[float],
        limit: int = 5,
        score_threshold: float = 0.3
    ) -> list[dict[str, Any]]:
        """Search for similar embeddings."""
        try:
            vector_manager = await get_vector_manager()
            
            search_results = await vector_manager.search_session_context(
                session_id=session_id,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
            )
            
            return search_results
            
        except Exception as exc:
            _logger.error(f"Failed to search embeddings: {str(exc)}")
            return []
    
    async def delete_embeddings(
        self,
        session_id: str,
        agent_id: str,
        embedding_ids: list[str] | None = None
    ) -> bool:
        """Delete embeddings from vector store."""
        try:
            vector_manager = await get_vector_manager()
            collection_name = f"{self.collection_prefix}_{agent_id}"
            
            await vector_manager.delete_vectors(
                collection_name=collection_name,
                vector_ids=embedding_ids or []
            )
            
            return True
            
        except Exception as exc:
            _logger.error(f"Failed to delete embeddings: {str(exc)}")
            return False
