"""Semantic retrieval operations for memory."""

from typing import Any, Dict, List, Optional

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.memory.embeddings.providers import EmbeddingProvider
from omnimind_backend.memory.embeddings.similarity import cosine_similarity
from omnimind_backend.memory.storage.database import MemoryDatabase
from omnimind_backend.memory.storage.vector_db import MemoryVectorDB

_logger = get_logger(__name__)


class SemanticRetriever:
    """Semantic search and retrieval for memory."""
    
    def __init__(self, embedding_dims: int = 768):
        self.embedding_provider = EmbeddingProvider(embedding_dims)
        self.memory_db = MemoryDatabase()
        self.vector_db = MemoryVectorDB()
        self.logger = _logger
    
    async def search_context(
        self,
        session_id: str,
        agent_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Search for semantically similar context."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_provider.generate_embedding(query)
            
            # Search vector database
            vector_results = await self.vector_db.search_embeddings(
                session_id=session_id,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=min_score,
                filters={"agent_id": agent_id}
            )
            
            # Enrich results with database content
            enriched_results = []
            with self.memory_db.get_db_session() as db:
                for result in vector_results:
                    # Get full content from database
                    embedding_id = result.get("id")
                    if embedding_id:
                        # This would need to be implemented based on the actual schema
                        enriched_result = {
                            **result,
                            "agent_id": agent_id,
                            "session_id": session_id,
                            "retrieval_method": "semantic_search"
                        }
                        enriched_results.append(enriched_result)
            
            # Sort by score and limit results
            enriched_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            return enriched_results[:top_k]
            
        except Exception as exc:
            self.logger.error(f"Semantic search failed: {str(exc)}")
            return []
    
    async def retrieve_similar_events(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve similar memory events."""
        try:
            # Generate embedding for content
            content_embedding = self.embedding_provider.generate_embedding(content)
            
            # Search for similar embeddings
            similar_embeddings = await self.vector_db.search_embeddings(
                session_id=session_id,
                query_vector=content_embedding,
                limit=limit,
                score_threshold=0.2
            )
            
            # Get corresponding events
            similar_events = []
            with self.memory_db.get_db_session() as db:
                for embedding in similar_embeddings:
                    source_id = embedding.get("source_id")
                    source_type = embedding.get("source_type")
                    
                    if source_type == "event" and source_id:
                        # Get the actual event from database
                        event = self.memory_db.get_memory_event_by_id(db, source_id)
                        if event:
                            similar_events.append({
                                "event": event,
                                "similarity_score": embedding.get("score", 0.0),
                                "embedding_id": embedding.get("id")
                            })
            
            return similar_events
            
        except Exception as exc:
            self.logger.error(f"Failed to retrieve similar events: {str(exc)}")
            return []
    
    def calculate_relevance_score(
        self,
        query_embedding: List[float],
        candidate_embedding: List[float]
    ) -> float:
        """Calculate relevance score between query and candidate."""
        return cosine_similarity(query_embedding, candidate_embedding)
