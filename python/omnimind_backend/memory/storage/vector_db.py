"""Vector database operations for memory."""

from typing import Any, Dict, List, Optional

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.services.vector_manager import get_vector_manager

_logger = get_logger(__name__)


class MemoryVectorDB:
    """Vector database operations for memory embeddings."""
    
    def __init__(self):
        self.logger = _logger
    
    async def create_collection(self, session_id: str, dimension: int = 768) -> bool:
        """Create vector collection for session."""
        try:
            vector_manager = await get_vector_manager()
            await vector_manager.create_session_collection(session_id)
            return True
        except Exception as exc:
            self.logger.error(f"Failed to create collection: {str(exc)}")
            return False
    
    async def store_embeddings(
        self,
        session_id: str,
        embeddings: List[Dict[str, Any]]
    ) -> List[str]:
        """Store embeddings in vector database."""
        try:
            vector_manager = await get_vector_manager()
            vector_ids = await vector_manager.store_session_embeddings(
                session_id=session_id,
                embeddings=embeddings,
            )
            return vector_ids
        except Exception as exc:
            self.logger.error(f"Failed to store embeddings: {str(exc)}")
            return []
    
    async def search_embeddings(
        self,
        session_id: str,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        try:
            vector_manager = await get_vector_manager()
            results = await vector_manager.search_session_context(
                session_id=session_id,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )
            
            # Apply filters if provided
            if filters:
                results = [
                    result for result in results
                    if all(result.get("metadata", {}).get(k) == v for k, v in filters.items())
                ]
            
            return results
        except Exception as exc:
            self.logger.error(f"Failed to search embeddings: {str(exc)}")
            return []
    
    async def delete_embeddings(
        self,
        session_id: str,
        vector_ids: Optional[List[str]] = None
    ) -> bool:
        """Delete embeddings from vector database."""
        try:
            vector_manager = await get_vector_manager()
            await vector_manager.delete_vectors(
                collection_name=f"session_{session_id}",
                vector_ids=vector_ids or [],
            )
            return True
        except Exception as exc:
            self.logger.error(f"Failed to delete embeddings: {str(exc)}")
            return False
    
    async def get_collection_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a collection."""
        try:
            vector_manager = await get_vector_manager()
            # This would need to be implemented in vector_manager
            # For now, return placeholder
            return {
                "session_id": session_id,
                "vector_count": 0,
                "dimension": 768,
                "created_at": None
            }
        except Exception as exc:
            self.logger.error(f"Failed to get collection stats: {str(exc)}")
            return {}
