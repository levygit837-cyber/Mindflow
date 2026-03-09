"""Memory integration for orchestrator.

Integrates the simple memory service into the orchestrator
for automatic context storage and retrieval.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import asyncio
from datetime import datetime

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.memory import create_memory_service, MemoryService
from mindflow_backend.services.nlp_embeddings import EmbeddingMethod

_logger = get_logger(__name__)


class MemoryIntegration:
    """Memory integration for orchestrator."""
    
    def __init__(
        self,
        db_path: str = "orchestrator_memory.db",
        embedding_method: EmbeddingMethod = EmbeddingMethod.TFIDF,
        auto_store: bool = True,
        auto_retrieve: bool = True,
        **memory_kwargs: Any,
    ) -> None:
        """Initialize memory integration.
        
        Args:
            db_path: Database path for memory storage.
            embedding_method: Embedding generation method.
            auto_store: Automatically store all interactions.
            auto_retrieve: Automatically retrieve context for agents.
            **memory_kwargs: Additional memory service configuration.
        """
        self.memory_service: Optional[MemoryService] = None
        self.db_path = db_path
        self.embedding_method = embedding_method
        self.auto_store = auto_store
        self.auto_retrieve = auto_retrieve
        self.memory_kwargs = memory_kwargs
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize memory service."""
        if self.is_initialized:
            return
        
        self.memory_service = create_memory_service(
            db_path=self.db_path,
            embedding_method=self.embedding_method,
            **self.memory_kwargs
        )
        
        await self.memory_service.initialize()
        self.is_initialized = True
        
        _logger.info(f"Memory integration initialized with {self.embedding_method}")
    
    async def store_interaction(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        token_start: int,
        token_end: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store an interaction in memory.
        
        Args:
            session_id: Session identifier.
            agent_id: Agent identifier.
            content: Interaction content.
            token_start: Start token position.
            token_end: End token position.
            metadata: Additional metadata.
            
        Returns:
            Context entry ID.
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.auto_store:
            return ""
        
        try:
            context_id = await self.memory_service.store_context(
                session_id=session_id,
                agent_id=agent_id,
                content=content,
                token_start=token_start,
                token_end=token_end,
                metadata=metadata or {
                    "stored_at": datetime.utcnow().isoformat(),
                    "auto_stored": True,
                }
            )
            
            _logger.debug(f"Stored interaction: {context_id} for session {session_id}")
            return context_id
            
        except Exception as e:
            _logger.error(f"Failed to store interaction: {e}")
            return ""
    
    async def retrieve_context(
        self,
        session_id: str,
        query: Optional[str] = None,
        token_range: Optional[Tuple[int, int]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve context for a session.
        
        Args:
            session_id: Session identifier.
            query: Optional search query.
            token_range: Optional token range filter.
            limit: Maximum results.
            
        Returns:
            Retrieved context entries.
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.auto_retrieve:
            return []
        
        try:
            if query:
                # Semantic search
                results = await self.memory_service.search_context(
                    session_id=session_id,
                    query=query,
                    token_range=token_range,
                    limit=limit,
                )
                return [
                    {
                        "id": entry.id,
                        "content": entry.content,
                        "agent_id": entry.agent_id,
                        "token_start": entry.token_start,
                        "token_end": entry.token_end,
                        "timestamp": entry.timestamp.isoformat(),
                        "similarity": similarity,
                        "metadata": entry.metadata,
                    }
                    for entry, similarity in results
                ]
            else:
                # Token range retrieval
                entries = await self.memory_service.get_context(
                    session_id=session_id,
                    token_start=token_range[0] if token_range else None,
                    token_end=token_range[1] if token_range else None,
                )
                return [
                    {
                        "id": entry.id,
                        "content": entry.content,
                        "agent_id": entry.agent_id,
                        "token_start": entry.token_start,
                        "token_end": entry.token_end,
                        "timestamp": entry.timestamp.isoformat(),
                        "metadata": entry.metadata,
                    }
                    for entry in entries
                ]
                
        except Exception as e:
            _logger.error(f"Failed to retrieve context: {e}")
            return []
    
    async def get_session_memory_summary(self, session_id: str) -> Dict[str, Any]:
        """Get memory summary for a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Session memory summary.
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            stats = await self.memory_service.get_session_stats(session_id)
            
            return {
                "session_id": session_id,
                "total_entries": stats["entry_count"],
                "token_range": [stats["min_token"], stats["max_token"]],
                "total_tokens": stats["total_tokens"],
                "embedding_method": self.embedding_method.value,
                "auto_store": self.auto_store,
                "auto_retrieve": self.auto_retrieve,
            }
            
        except Exception as e:
            _logger.error(f"Failed to get session summary: {e}")
            return {"session_id": session_id, "error": str(e)}
    
    async def cleanup_session(self, session_id: str) -> int:
        """Clean up old context in a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Number of entries removed.
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            removed_count = await self.memory_service.cleanup_session(session_id)
            _logger.info(f"Cleaned up {removed_count} entries from session {session_id}")
            return removed_count
            
        except Exception as e:
            _logger.error(f"Failed to cleanup session: {e}")
            return 0


# Global memory integration instance
_memory_integration: Optional[MemoryIntegration] = None


def get_memory_integration() -> MemoryIntegration:
    """Get global memory integration instance.
    
    Returns:
        Memory integration instance.
    """
    global _memory_integration
    if _memory_integration is None:
        _memory_integration = MemoryIntegration()
    return _memory_integration


async def initialize_memory_integration(
    db_path: str = "orchestrator_memory.db",
    embedding_method: EmbeddingMethod = EmbeddingMethod.TFIDF,
    **kwargs: Any,
) -> MemoryIntegration:
    """Initialize global memory integration.
    
    Args:
        db_path: Database path.
        embedding_method: Embedding method.
        **kwargs: Additional configuration.
        
    Returns:
        Initialized memory integration.
    """
    global _memory_integration
    _memory_integration = MemoryIntegration(
        db_path=db_path,
        embedding_method=embedding_method,
        **kwargs
    )
    await _memory_integration.initialize()
    return _memory_integration


# ---------------------------------------------------------------------------
# Orchestrator Integration Functions
# ---------------------------------------------------------------------------

async def store_orchestrator_interaction(
    session_id: str,
    agent_id: str,
    message: str,
    response: str,
    token_start: int,
    token_end: int,
) -> Tuple[str, str]:
    """Store orchestrator interaction (message + response).
    
    Args:
        session_id: Session identifier.
        agent_id: Agent identifier.
        message: User message.
        response: Agent response.
        token_start: Start token position.
        token_end: End token position.
        
    Returns:
        Tuple of (message_id, response_id).
    """
    memory_integration = get_memory_integration()
    
    # Store user message
    message_id = await memory_integration.store_interaction(
        session_id=session_id,
        agent_id="user",
        content=message,
        token_start=token_start,
        token_end=token_start + len(message.split()),
        metadata={"type": "user_message"},
    )
    
    # Store agent response
    response_id = await memory_integration.store_interaction(
        session_id=session_id,
        agent_id=agent_id,
        content=response,
        token_start=token_start + len(message.split()),
        token_end=token_end,
        metadata={"type": "agent_response"},
    )
    
    return message_id, response_id


async def get_context_for_agent(
    session_id: str,
    query: str,
    token_range: Optional[Tuple[int, int]] = None,
    limit: int = 5,
) -> str:
    """Get formatted context for agent.
    
    Args:
        session_id: Session identifier.
        query: Search query.
        token_range: Optional token range.
        limit: Maximum results.
        
    Returns:
        Formatted context string.
    """
    memory_integration = get_memory_integration()
    
    context_entries = await memory_integration.retrieve_context(
        session_id=session_id,
        query=query,
        token_range=token_range,
        limit=limit,
    )
    
    if not context_entries:
        return ""
    
    # Format context entries
    context_parts = []
    for entry in context_entries:
        context_parts.append(
            f"[{entry['agent_id']} @ tokens {entry['token_start']}-{entry['token_end']}]: {entry['content']}"
        )
    
    return "\n".join(context_parts)


async def get_token_range_context(
    session_id: str,
    start_token: int,
    end_token: int,
) -> str:
    """Get context from specific token range.
    
    Args:
        session_id: Session identifier.
        start_token: Start token position.
        end_token: End token position.
        
    Returns:
        Formatted context string.
    """
    memory_integration = get_memory_integration()
    
    context_entries = await memory_integration.retrieve_context(
        session_id=session_id,
        token_range=(start_token, end_token),
    )
    
    if not context_entries:
        return ""
    
    # Format context entries in chronological order
    context_parts = []
    for entry in sorted(context_entries, key=lambda x: x['token_start']):
        context_parts.append(
            f"[{entry['agent_id']} @ {entry['token_start']}-{entry['token_end']}]: {entry['content']}"
        )
    
    return "\n".join(context_parts)
