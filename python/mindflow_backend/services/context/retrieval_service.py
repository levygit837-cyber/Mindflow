"""Context retrieval service for semantic and range-based context access.

This service provides comprehensive context retrieval with support for
different retrieval modes, caching, and intelligent context optimization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.context_interfaces import RetrievalServiceInterface


class RetrievalService(BaseAbstractService, RetrievalServiceInterface):
    """Service for retrieving context from sessions and token windows.
    
    This service provides multiple retrieval modes including range-based,
    topic-based, and semantic search with intelligent caching and optimization.
    """
    
    def __init__(self) -> None:
        """Initialize retrieval service with dependencies."""
        super().__init__()
        
        # Lazy load dependencies
        self._memory_service = None
        self._vector_service = None
        self._embedding_service = None
        
        # Cache for retrieval results
        self._retrieval_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Retrieval configuration
        self._default_limit = 10
        self._max_context_length = 100000  # 100k characters
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_memory_service(self):
        """Get memory service instance (lazy loading)."""
        if self._memory_service is None:
            from mindflow_backend.memory import get_memory_service
            self._memory_service = get_memory_service()
        return self._memory_service
    
    def _get_vector_service(self):
        """Get vector service instance (lazy loading)."""
        if self._vector_service is None:
            from mindflow_backend.services import get_vector_service
            self._vector_service = get_vector_service()
        return self._vector_service
    
    def _get_embedding_service(self):
        """Get embedding service instance (lazy loading)."""
        if self._embedding_service is None:
            from mindflow_backend.services import get_embedding_service
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    async def retrieve_context(
        self,
        query: str,
        session_id: str,
        retrieval_mode: str = "semantic",
        limit: int = 10
    ) -> dict[str, Any]:
        """Retrieve context for query using specified mode.
        
        Args:
            query: Search query
            session_id: Session identifier
            retrieval_mode: Retrieval mode (semantic, range, topic)
            limit: Maximum number of results
            
        Returns:
            Dictionary containing retrieved context
        """
        self.log_operation(
            "retrieve_context",
            session_id=session_id,
            retrieval_mode=retrieval_mode,
            query_length=len(query),
            limit=limit
        )
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(query, session_id, retrieval_mode, limit)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Route to appropriate retrieval method
            if retrieval_mode == "range":
                result = await self._retrieve_by_range(query, session_id, limit)
            elif retrieval_mode == "topic":
                result = await self._retrieve_by_topic(query, session_id, limit)
            elif retrieval_mode == "semantic":
                result = await self._retrieve_by_semantic(query, session_id, limit)
            else:
                raise ValueError(f"Unsupported retrieval mode: {retrieval_mode}")
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as exc:
            self._logger.error(f"Error retrieving context: {str(exc)}")
            raise
    
    async def search_by_range(
        self,
        session_id: str,
        token_range: tuple[int, int]
    ) -> dict[str, Any]:
        """Search context by token range.
        
        Args:
            session_id: Session identifier
            token_range: Token range (start, end)
            
        Returns:
            Dictionary containing range-based context
        """
        self.log_operation("search_by_range", session_id=session_id, token_range=token_range)
        
        try:
            memory_service = self._get_memory_service()
            context_window = await memory_service.get_context_window(
                session_id=session_id,
                window_start=token_range[0],
                window_end=token_range[1]
            )
            
            return {
                "session_id": session_id,
                "retrieval_mode": "range",
                "token_range": token_range,
                "context": context_window.get("context", ""),
                "event_count": context_window.get("event_count", 0),
                "total_tokens": context_window.get("total_tokens", 0),
                "retrieved_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error searching by range: {str(exc)}")
            raise
    
    async def search_by_topic(
        self,
        query: str,
        session_id: str,
        topic_filters: list[str] | None = None
    ) -> dict[str, Any]:
        """Search context by topic filtering.
        
        Args:
            query: Search query
            session_id: Session identifier
            topic_filters: Optional topic filters
            
        Returns:
            Dictionary containing topic-based context
        """
        self.log_operation(
            "search_by_topic",
            session_id=session_id,
            query_length=len(query),
            topic_filters=topic_filters
        )
        
        try:
            # Get recent memory events
            memory_service = self._get_memory_service()
            memory_data = await memory_service.get_agent_memory("session", session_id, token_limit=5000)
            
            # Filter events by topic keywords
            filtered_events = []
            query_lower = query.lower()
            
            for event in memory_data.get("recent_events", []):
                event_content = event.get("content", "").lower()
                
                # Check if event matches query or topic filters
                matches_query = any(word in event_content for word in query_lower.split())
                matches_topics = True
                
                if topic_filters:
                    matches_topics = any(topic.lower() in event_content for topic in topic_filters)
                
                if matches_query or matches_topics:
                    filtered_events.append(event)
            
            # Build context from filtered events
            context_parts = []
            for event in filtered_events[:20]:  # Limit to prevent too large context
                context_parts.append(f"{event['role']}: {event['content']}")
            
            context = "\n\n".join(context_parts)
            
            return {
                "session_id": session_id,
                "retrieval_mode": "topic",
                "query": query,
                "topic_filters": topic_filters or [],
                "context": context,
                "event_count": len(filtered_events),
                "filtered_events": len(filtered_events),
                "retrieved_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error searching by topic: {str(exc)}")
            raise
    
    async def search_semantic(
        self,
        query: str,
        session_id: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> dict[str, Any]:
        """Search context semantically using vector similarity.
        
        Args:
            query: Search query
            session_id: Session identifier
            similarity_threshold: Minimum similarity score
            max_results: Maximum number of results
            
        Returns:
            Dictionary containing semantic search results
        """
        self.log_operation(
            "search_semantic",
            session_id=session_id,
            query_length=len(query),
            similarity_threshold=similarity_threshold,
            max_results=max_results
        )
        
        try:
            # Use memory service semantic search
            memory_service = self._get_memory_service()
            semantic_results = await memory_service.search_semantic_context(
                query=query,
                session_id=session_id,
                top_k=max_results,
                min_score=similarity_threshold
            )
            
            # Build context from semantic results
            context_parts = []
            references = []
            
            for result in semantic_results:
                context_parts.append(f"({result['agent_type']} - {result['role']}): {result['content']}")
                references.append(f"semantic_{result['event_id']}")
            
            context = "\n\n".join(context_parts)
            
            return {
                "session_id": session_id,
                "retrieval_mode": "semantic",
                "query": query,
                "context": context,
                "results": semantic_results,
                "result_count": len(semantic_results),
                "similarity_threshold": similarity_threshold,
                "references": references,
                "retrieved_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error searching semantically: {str(exc)}")
            raise
    
    async def get_context_summary(
        self,
        session_id: str,
        context_window: tuple[int, int]
    ) -> dict[str, Any]:
        """Get context summary for a token window.
        
        Args:
            session_id: Session identifier
            context_window: Token window range
            
        Returns:
            Dictionary containing context summary
        """
        self.log_operation("get_context_summary", session_id=session_id, context_window=context_window)
        
        try:
            # Get context window data
            range_result = await self.search_by_range(session_id, context_window)
            
            # Generate summary (simplified - would use LLM in production)
            context = range_result.get("context", "")
            
            # Create basic summary
            if context:
                lines = context.split('\n')
                summary_lines = [
                    f"Context window: {context_window[0]}-{context_window[1]}",
                    f"Total lines: {len(lines)}",
                    f"Characters: {len(context)}",
                    "Content preview: " + context[:200] + "..." if len(context) > 200 else context
                ]
                summary = "\n".join(summary_lines)
            else:
                summary = f"No context found for window {context_window[0]}-{context_window[1]}"
            
            return {
                "session_id": session_id,
                "context_window": context_window,
                "summary": summary,
                "full_context": context,
                "generated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting context summary: {str(exc)}")
            raise
    
    async def update_context_index(
        self,
        session_id: str,
        new_content: str
    ) -> dict[str, Any]:
        """Update context search index with new content.
        
        Args:
            session_id: Session identifier
            new_content: New content to index
            
        Returns:
            Dictionary containing update result
        """
        self.log_operation(
            "update_context_index",
            session_id=session_id,
            content_length=len(new_content)
        )
        
        try:
            # Generate embedding for new content
            embedding_service = self._get_embedding_service()
            embedding = await embedding_service.generate_embedding(new_content)
            
            # Store in vector database
            vector_service = self._get_vector_service()
            vector_id = str(uuid4())
            
            await vector_service.insert_vectors(
                collection_name=f"session_context_{session_id}",
                vectors=[{
                    "id": vector_id,
                    "vector": embedding,
                    "metadata": {
                        "session_id": session_id,
                        "content": new_content[:500],  # Store preview
                        "content_length": len(new_content),
                        "indexed_at": datetime.now(UTC).isoformat()
                    }
                }]
            )
            
            # Clear relevant cache entries
            self._clear_cache_for_session(session_id)
            
            return {
                "session_id": session_id,
                "vector_id": vector_id,
                "content_length": len(new_content),
                "indexed_at": datetime.now(UTC).isoformat(),
                "status": "indexed"
            }
            
        except Exception as exc:
            self._logger.error(f"Error updating context index: {str(exc)}")
            raise
    
    # Advanced retrieval methods
    
    async def hybrid_search(
        self,
        query: str,
        session_id: str,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10
    ) -> dict[str, Any]:
        """Perform hybrid search combining semantic and keyword matching.
        
        Args:
            query: Search query
            session_id: Session identifier
            semantic_weight: Weight for semantic results
            keyword_weight: Weight for keyword results
            limit: Maximum number of results
            
        Returns:
            Dictionary containing hybrid search results
        """
        self.log_operation(
            "hybrid_search",
            session_id=session_id,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight
        )
        
        try:
            # Get semantic results
            semantic_result = await self.search_semantic(query, session_id, max_results=limit)
            
            # Get keyword-based results
            keyword_result = await self.search_by_topic(query, session_id)
            
            # Combine and re-score results
            combined_results = []
            
            # Add semantic results with weighted scores
            for i, result in enumerate(semantic_result.get("results", [])):
                combined_results.append({
                    "content": result["content"],
                    "agent_type": result["agent_type"],
                    "role": result["role"],
                    "score": result["score"] * semantic_weight,
                    "source": "semantic",
                    "original_score": result["score"]
                })
            
            # Add keyword results with weighted scores
            keyword_context = keyword_result.get("context", "")
            if keyword_context:
                # Simple keyword matching score
                query_words = set(query.lower().split())
                content_words = set(keyword_context.lower().split())
                overlap = len(query_words.intersection(content_words))
                keyword_score = overlap / len(query_words) if query_words else 0.0
                
                combined_results.append({
                    "content": keyword_context,
                    "agent_type": "session",
                    "role": "mixed",
                    "score": keyword_score * keyword_weight,
                    "source": "keyword",
                    "original_score": keyword_score
                })
            
            # Sort by combined score
            combined_results.sort(key=lambda x: x["score"], reverse=True)
            
            # Build final context
            context_parts = [result["content"] for result in combined_results[:limit]]
            final_context = "\n\n".join(context_parts)
            
            return {
                "session_id": session_id,
                "query": query,
                "retrieval_mode": "hybrid",
                "context": final_context,
                "results": combined_results[:limit],
                "result_count": len(combined_results[:limit]),
                "semantic_weight": semantic_weight,
                "keyword_weight": keyword_weight,
                "retrieved_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error in hybrid search: {str(exc)}")
            raise
    
    async def get_retrieval_statistics(self, session_id: str) -> dict[str, Any]:
        """Get retrieval statistics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing retrieval statistics
        """
        self.log_operation("get_retrieval_statistics", session_id=session_id)
        
        try:
            # Get memory statistics
            memory_service = self._get_memory_service()
            memory_summary = await memory_service.get_session_memory_summary(session_id)
            
            # Get vector collection statistics
            vector_service = self._get_vector_service()
            try:
                collection_stats = await vector_service.get_collection_stats(f"session_context_{session_id}")
            except Exception:
                collection_stats = {"vector_count": 0}
            
            # Get cache statistics
            cache_stats = {
                "cached_entries": len([k for k in self._retrieval_cache.keys() if session_id in k]),
                "total_cache_size": len(self._retrieval_cache)
            }
            
            return {
                "session_id": session_id,
                "memory_stats": memory_summary,
                "vector_stats": collection_stats,
                "cache_stats": cache_stats,
                "generated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting retrieval statistics: {str(exc)}")
            raise
    
    # Helper methods
    
    async def _retrieve_by_range(self, query: str, session_id: str, limit: int) -> dict[str, Any]:
        """Retrieve context by range (placeholder implementation)."""
        # For range-based retrieval, we need token positions from the query
        # This is a simplified implementation
        start_token = 0
        end_token = 5000  # Default range
        
        return await self.search_by_range(session_id, (start_token, end_token))
    
    async def _retrieve_by_topic(self, query: str, session_id: str, limit: int) -> dict[str, Any]:
        """Retrieve context by topic."""
        return await self.search_by_topic(query, session_id)
    
    async def _retrieve_by_semantic(self, query: str, session_id: str, limit: int) -> dict[str, Any]:
        """Retrieve context semantically."""
        return await self.search_semantic(query, session_id, max_results=limit)
    
    def _get_cache_key(self, query: str, session_id: str, mode: str, limit: int) -> str:
        """Generate cache key for retrieval result."""
        import hashlib
        key_parts = [query[:100], session_id, mode, str(limit)]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached result if still valid."""
        if cache_key in self._retrieval_cache:
            cached = self._retrieval_cache[cache_key]
            cache_age = (datetime.now(UTC) - datetime.fromisoformat(cached["cached_at"])).total_seconds()
            
            if cache_age < self._cache_ttl:
                return cached
            else:
                # Remove expired cache entry
                del self._retrieval_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: dict[str, Any]) -> None:
        """Cache retrieval result."""
        result["cached_at"] = datetime.now(UTC).isoformat()
        self._retrieval_cache[cache_key] = result
    
    def _clear_cache_for_session(self, session_id: str) -> None:
        """Clear cache entries for a specific session."""
        keys_to_remove = [k for k in self._retrieval_cache.keys() if session_id in k]
        for key in keys_to_remove:
            del self._retrieval_cache[key]
