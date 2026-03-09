"""Context retriever for memory service.

Simplified context retrieval focused on token ranges
and semantic similarity search.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from mindflow_backend.infra.logging import get_logger
from .context_storage import SimpleContextStorage
from ..nlp_embeddings import NLPEmbeddingService

_logger = get_logger(__name__)


class SimpleContextRetriever:
    """Simplified context retriever."""
    
    def __init__(
        self,
        storage: SimpleContextStorage,
        embedding_service: NLPEmbeddingService,
        similarity_threshold: float = 0.3,
    ) -> None:
        """Initialize context retriever.
        
        Args:
            storage: Context storage instance.
            embedding_service: Embedding service.
            similarity_threshold: Minimum similarity threshold.
        """
        self.storage = storage
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
    
    async def get_by_token_range(
        self,
        session_id: str,
        token_start: Optional[int] = None,
        token_end: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get context by token range.
        
        Args:
            session_id: Session identifier.
            token_start: Start token position.
            token_end: End token position.
            limit: Maximum entries.
            
        Returns:
            Context entries in token range.
        """
        return await self.storage.get_by_token_range(
            session_id, token_start, token_end, limit
        )
    
    async def search_by_query(
        self,
        session_id: str,
        query: str,
        token_range: Optional[Tuple[int, int]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search context by semantic similarity.
        
        Args:
            session_id: Session identifier.
            query: Search query.
            token_range: Optional token range filter.
            limit: Maximum results.
            
        Returns:
            Search results with similarity scores.
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embeddings(query)
        
        # Search by similarity
        results = await self.storage.search_by_embedding(
            session_id,
            query_embedding[0],
            limit,
            self.similarity_threshold,
        )
        
        # Filter by token range if specified
        if token_range:
            token_start, token_end = token_range
            filtered_results = []
            
            for result in results:
                if (result["token_start"] >= token_start and 
                    result["token_end"] <= token_end):
                    filtered_results.append(result)
            
            results = filtered_results
        
        return results
    
    async def get_recent(
        self,
        session_id: str,
        token_count: int = 1000,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent context by token count.
        
        Args:
            session_id: Session identifier.
            token_count: Number of recent tokens.
            limit: Maximum entries.
            
        Returns:
            Recent context entries.
        """
        # Get session stats
        stats = await self.storage.get_session_stats(session_id)
        max_token = stats["max_token"]
        
        # Get recent entries
        return await self.get_by_token_range(
            session_id,
            max(0, max_token - token_count),
            max_token,
            limit,
        )


# Alias for backward compatibility
ContextRetriever = SimpleContextRetriever
