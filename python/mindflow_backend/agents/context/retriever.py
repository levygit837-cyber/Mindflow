"""Agent context retriever integration.

Provides RAG-based context retrieval for agents with automatic
context injection and real-time updates during execution.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.interfaces.core import ContextRetriever, VectorStore, Cache
from mindflow_backend.agents.core.exceptions import ContextRetrievalError, VectorStoreError
from mindflow_backend.schemas.session.contracts import RetrievedContext
from mindflow_backend.services.session_retriever import SessionRetrieverService
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.agents.context.cache import get_context_cache
from mindflow_backend.agents.context.vector_store import get_vector_store, get_embedding_provider
from mindflow_backend.config.agents import get_agent_config

_logger = get_logger(__name__)


class AgentContextRetriever:
    """RAG-based context retrieval for agents."""
    
    def __init__(
        self,
        agent_id: str,
        vector_store: VectorStore | None = None,
        session_retriever: SessionRetrieverService | None = None,
        cache: Cache | None = None,
    ) -> None:
        """Initialize context retriever for a specific agent.
        
        Args:
            agent_id: ID of the agent
            vector_store: Vector store implementation
            session_retriever: Session retriever service
            cache: Cache implementation
        """
        self.agent_id = agent_id
        self.vector_store = vector_store
        self.session_retriever = session_retriever or SessionRetrieverService()
        self.cache = cache or get_context_cache()
        self.config = get_agent_config()
        self.embedding_provider = get_embedding_provider()
        
        _logger.info("agent_context_retriever_initialized", agent_id=agent_id)
    
    async def initialize(self) -> None:
        """Initialize the context retriever services."""
        if self.vector_store is None:
            self.vector_store = await get_vector_store()
        
        _logger.info("agent_context_retriever_services_initialized", agent_id=self.agent_id)
    
    async def get_relevant_context(
        self,
        agent_id: str,
        query: str,
        session_id: str,
        context_window: tuple[int, int] = (0, 100000),
        include_related: bool = True,
        max_results: int = 5,
    ) -> RetrievedContext:
        """
        Retrieve relevant context using:
        1. Vector similarity search
        2. Token range filtering
        3. Session hierarchy traversal
        
        Args:
            agent_id: ID of the agent requesting context
            query: Query for semantic search
            session_id: Session ID to search within
            context_window: Token range to consider
            include_related: Whether to include related sessions
            max_results: Maximum number of results to return
            
        Returns:
            RetrievedContext with relevant information
        """
        _logger.info(
            "agent_context_retrieval_started",
            agent_id=agent_id,
            session_id=session_id,
            query=query,
            context_window=context_window,
        )
        
        if not self.vector_store:
            await self.initialize()
        
        # Check cache first
        cache_key = self._generate_cache_key(session_id, context_window, query)
        cached_context = self.cache.get(cache_key)
        if cached_context:
            _logger.info("agent_context_cache_hit", cache_key=cache_key)
            return cached_context
        
        # Perform semantic search if query is provided
        if query:
            try:
                # Generate query vector using embedding model
                query_vector = await self.embedding_provider.generate_embedding(query)
                
                # Search for similar vectors
                search_results = await self.vector_store.search_session_context(
                    session_id=session_id,
                    query_vector=query_vector,
                    limit=max_results,
                    score_threshold=self.config.context_similarity_threshold,
                )
                
                # Combine search results with range-based retrieval
                context_content = self._format_search_results(search_results, query)
            except VectorStoreError as e:
                _logger.warning("vector_search_failed", error=str(e), fallback="range_based")
                context_content = await self._get_range_context(session_id, context_window)
        else:
            # Fallback to range-based retrieval
            context_content = await self._get_range_context(session_id, context_window)
        
        retrieved_context = RetrievedContext(
            context_id=self._generate_context_id(),
            session_id=session_id,
            query=query,
            context_windows=[context_window],
            content=context_content,
            relevance_score=0.8,  # TODO: Calculate actual relevance
            source_sessions=[session_id],
            metadata={
                "agent_id": agent_id,
                "retrieval_method": "semantic" if query else "range",
                "include_related": include_related,
            },
        )
        
        # Cache the result
        self.cache.set(cache_key, retrieved_context, ttl=self.config.cache_ttl_seconds)
        
        _logger.info(
            "agent_context_retrieval_completed",
            agent_id=agent_id,
            session_id=session_id,
            relevance_score=retrieved_context.relevance_score,
        )
        
        return retrieved_context
    
    async def get_context_window(
        self,
        session_id: str,
        token_range: tuple[int, int],
        include_related: bool = False,
    ) -> RetrievedContext:
        """
        Get context from a specific token window.
        
        Args:
            session_id: Session identifier
            token_range: Token range to retrieve (start, end)
            include_related: Whether to include related sessions
            
        Returns:
            RetrievedContext with the requested window content
        """
        _logger.info(
            "agent_context_window_requested",
            agent_id=self.agent_id,
            session_id=session_id,
            token_range=token_range,
        )
        
        context = await self.session_retriever.get_context_window(
            session_id=session_id,
            token_range=token_range,
            include_related=include_related,
        )
        
        # Add agent-specific metadata
        context.metadata["agent_id"] = self.agent_id
        context.metadata["retrieved_by"] = "agent_context_window"
        
        return context
    
    async def get_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[RetrievedContext]:
        """
        Get context using semantic search.
        
        Args:
            query: Search query
            session_id: Session identifier
            top_k: Maximum number of results
            min_score: Minimum relevance score
            
        Returns:
            List of RetrievedContext objects
        """
        _logger.info(
            "agent_semantic_context_requested",
            agent_id=self.agent_id,
            session_id=session_id,
            query=query,
            top_k=top_k,
        )
        
        contexts = await self.session_retriever.get_semantic_context(
            query=query,
            session_id=session_id,
            top_k=top_k,
            min_score=min_score,
        )
        
        # Add agent-specific metadata to each context
        for context in contexts:
            context.metadata["agent_id"] = self.agent_id
            context.metadata["retrieved_by"] = "agent_semantic_search"
        
        return contexts
    
    async def inject_context_into_agent(
        self,
        agent_id: str,
        context: RetrievedContext,
    ) -> None:
        """
        Inject retrieved context into agent memory.
        
        Args:
            agent_id: Target agent ID
            context: Context to inject
        """
        _logger.info(
            "agent_context_injection_started",
            target_agent_id=agent_id,
            context_id=str(context.context_id),
            session_id=str(context.session_id),
        )
        
        # TODO: Implement actual context injection into agent memory
        # This would involve:
        # 1. Formatting context for agent consumption
        # 2. Adding to agent's working memory
        # 3. Updating agent's context window
        
        _logger.info(
            "agent_context_injection_completed",
            target_agent_id=agent_id,
            context_id=str(context.context_id),
        )
    
    async def update_context_during_execution(
        self,
        agent_id: str,
        session_id: str,
        new_content: str,
        token_count: int,
    ) -> None:
        """
        Update context in real-time during agent execution.
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            new_content: New content to add
            token_count: Token count of new content
        """
        _logger.info(
            "agent_context_update_started",
            agent_id=agent_id,
            session_id=session_id,
            token_count=token_count,
        )
        
        # TODO: Implement real-time context updates
        # This would involve:
        # 1. Creating embeddings for new content
        # 2. Storing in vector database
        # 3. Updating context cache
        
        # Clear relevant cache entries
        if hasattr(self.cache, 'invalidate_session'):
            self.cache.invalidate_session(session_id)
        else:
            # Fallback: clear all cache (less efficient)
            self.cache.clear()
        
        _logger.info(
            "agent_context_update_completed",
            agent_id=agent_id,
            session_id=session_id,
            cache_cleared=True,
        )
    
    async def store_execution_context(
        self,
        agent_id: str,
        session_id: str,
        execution_context: dict[str, Any],
    ) -> None:
        """
        Store agent execution context for future retrieval.
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            execution_context: Context data to store
        """
        _logger.info(
            "agent_execution_context_storage_started",
            agent_id=agent_id,
            session_id=session_id,
        )
        
        if not self.vector_store:
            await self.initialize()
        
        # Create collection for session if it doesn't exist
        await self.vector_store.create_session_collection(session_id)
        
        # Extract text content from execution context
        text_content = self._extract_text_from_context(execution_context)
        
        if text_content:
            # Create embedding for the content
            embedding = await self.embedding_provider.generate_embedding(text_content)
            
            # Store in vector store
            await self.vector_store.store_vectors(
                session_id=session_id,
                vectors=[{
                    "vector": embedding,
                    "content": text_content,
                    "metadata": {
                        "agent_id": agent_id,
                        "timestamp": self._get_timestamp(),
                        "context_type": "execution",
                    },
                }],
            )
        
        _logger.info(
            "agent_execution_context_stored",
            agent_id=agent_id,
            session_id=session_id,
        )
    
    def _format_search_results(
        self,
        search_results: list[dict[str, Any]],
        query: str,
    ) -> str:
        """Format search results into readable context."""
        if not search_results:
            return f"No relevant context found for query: {query}"
        
        context_parts = [f"Context for query: {query}"]
        for i, result in enumerate(search_results, 1):
            # TODO: Format actual search results
            context_parts.append(f"{i}. [Search result {i}]")
        
        return "\n\n".join(context_parts)
    
    async def _get_range_context(
        self,
        session_id: str,
        context_window: tuple[int, int],
    ) -> str:
        """Get context from a specific token range."""
        # TODO: Implement actual range-based context retrieval
        return f"Context from token range {context_window[0]}-{context_window[1]} in session {session_id}"
    
    def _generate_context_id(self) -> str:
        """Generate a unique context ID."""
        from uuid import uuid4
        return str(uuid4())
    
    def _generate_cache_key(
        self,
        session_id: str,
        context_window: tuple[int, int],
        query: str,
    ) -> str:
        """Generate a cache key from parameters."""
        import hashlib
        key_data = f"{session_id}:{context_window[0]}-{context_window[1]}:{hash(query)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _extract_text_from_context(self, execution_context: dict[str, Any]) -> str:
        """Extract text content from execution context."""
        # Simple implementation - concatenate string values
        text_parts = []
        
        for key, value in execution_context.items():
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        text_parts.append(f"{key}.{sub_key}: {sub_value}")
        
        return "\n".join(text_parts)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()


# Global agent context retriever instances
_agent_retrievers: dict[str, AgentContextRetriever] = {}


async def get_agent_context_retriever(agent_id: str) -> AgentContextRetriever:
    """Get or create a context retriever for an agent."""
    if agent_id not in _agent_retrievers:
        _agent_retrievers[agent_id] = AgentContextRetriever(agent_id)
        await _agent_retrievers[agent_id].initialize()
    return _agent_retrievers[agent_id]


async def inject_context_to_all_agents(
    context: RetrievedContext,
    agent_ids: list[str] | None = None,
) -> None:
    """Inject context into multiple agents."""
    # TODO: Implement batch context injection
    pass
