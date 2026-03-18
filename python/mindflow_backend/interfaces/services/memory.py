"""Memory service interfaces for MindFlow backend.

This module provides standardized interfaces for memory management services,
including storage, retrieval, and context operations.

Canonical facade
----------------
``MemoryFacadeInterface`` is the **single coherent contract** that all callers
should depend on.  The older ``MemoryServiceInterface``, ``ContextMemoryInterface``,
``VectorMemoryInterface`` and ``AgentMemoryServiceInterface`` are preserved for
backward compatibility with existing implementations but should not be used in
new code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from uuid import UUID

from mindflow_backend.schemas.memory.contracts import (
    AgentMemorySnapshot,
    MemoryPersistResult,
    MemoryRecallRequest,
    MemoryRecallResponse,
    SessionBlockSchema,
)


@runtime_checkable
class MemoryServiceInterface(Protocol):
    """Interface for memory management operations."""
    
    async def store_memory(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a memory entry.
        
        Args:
            session_id: Session identifier
            agent_id: Agent identifier
            content: Memory content
            metadata: Optional metadata
            
        Returns:
            Dictionary containing storage result
        """
        ...
    
    async def retrieve_memory(
        self,
        session_id: str,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve memory entries for a session.
        
        Args:
            session_id: Session identifier
            limit: Optional limit on results
            filters: Optional filters for retrieval
            
        Returns:
            List of memory entries
        """
        ...
    
    async def search_memory(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: Optional[int] = 10
    ) -> List[Dict[str, Any]]:
        """Search memory entries by content.
        
        Args:
            query: Search query
            session_id: Optional session filter
            limit: Optional limit on results
            
        Returns:
            List of matching memory entries
        """
        ...
    
    async def delete_memory(
        self,
        memory_id: str
    ) -> bool:
        """Delete a memory entry.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            True if deleted successfully
        """
        ...
    
    async def get_memory_stats(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get memory statistics.
        
        Args:
            session_id: Optional session filter
            
        Returns:
            Dictionary containing statistics
        """
        ...


@runtime_checkable
class ContextMemoryInterface(Protocol):
    """Interface for context-aware memory operations."""
    
    async def store_context(
        self,
        session_id: str,
        context_window: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store context window.
        
        Args:
            session_id: Session identifier
            context_window: List of context entries
            metadata: Optional metadata
            
        Returns:
            Dictionary containing storage result
        """
        ...
    
    async def retrieve_context(
        self,
        session_id: str,
        window_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve context window.
        
        Args:
            session_id: Session identifier
            window_size: Optional window size
            
        Returns:
            List of context entries
        """
        ...
    
    async def update_context(
        self,
        session_id: str,
        context_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update context window.
        
        Args:
            session_id: Session identifier
            context_updates: List of updates
            
        Returns:
            Dictionary containing update result
        """
        ...


@runtime_checkable
class VectorMemoryInterface(Protocol):
    """Interface for vector-based memory operations."""
    
    async def create_embedding(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """Create embedding for text.
        
        Args:
            text: Text to embed
            metadata: Optional metadata
            
        Returns:
            Vector embedding
        """
        ...
    
    async def search_similar(
        self,
        query_vector: List[float],
        limit: Optional[int] = 10,
        threshold: Optional[float] = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar memories by vector.
        
        Args:
            query_vector: Query vector
            limit: Optional limit on results
            threshold: Optional similarity threshold
            
        Returns:
            List of similar memories
        """
        ...
    
    async def store_embedding(
        self,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store text with embedding.
        
        Args:
            text: Text content
            embedding: Vector embedding
            metadata: Optional metadata
            
        Returns:
            Dictionary containing storage result
        """
        ...


class AgentMemoryServiceInterface(ABC):
    """Interface ABC para serviços de memória de agente.

    Define o contrato para gerenciar eventos, janelas de contexto e
    retrieval semântico dentro de uma sessão de agente.
    """

    @abstractmethod
    async def get_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        token_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retorna eventos e janelas de memória do agente."""
        ...

    @abstractmethod
    async def add_memory_event(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int,
        source_message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Adiciona evento de memória e gera embedding em tempo real."""
        ...

    @abstractmethod
    async def search_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Busca contexto semanticamente similar via pgvector."""
        ...

    @abstractmethod
    async def retrieve_context_for_query(
        self,
        query: str,
        session_id: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Recupera contexto relevante para uma query."""
        ...

    @abstractmethod
    async def create_memory_summary(
        self,
        agent_id: str,
        session_id: str,
        window_range: Tuple[int, int],
    ) -> Dict[str, Any]:
        """Cria sumário extrativista de uma janela de tokens."""
        ...

    @abstractmethod
    async def get_memory_windows(
        self,
        agent_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """Lista janelas de memória do agente na sessão."""
        ...

    @abstractmethod
    async def initialize_session_memory(
        self, session_id: str, agent_types: List[str]
    ) -> Dict[str, Any]:
        """Inicializa cursores e coleções para uma nova sessão."""
        ...

    @abstractmethod
    async def cleanup_session_memory(self, session_id: str) -> bool:
        """Remove dados de memória de uma sessão encerrada."""
        ...

    @abstractmethod
    async def get_session_memory_summary(self, session_id: str) -> Dict[str, Any]:
        """Retorna sumário consolidado de memória da sessão."""
        ...


@runtime_checkable
class MemoryFacadeInterface(Protocol):
    """Canonical facade contract for the memory subsystem.

    This is the *only* interface that new callers should depend on.
    Implementations must delegate to the underlying storage services.
    """

    async def record_message(
        self,
        db: Any,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> MemoryPersistResult:
        """Persist a message to agent memory and embed it immediately."""
        ...

    async def recall(
        self,
        request: MemoryRecallRequest,
    ) -> MemoryRecallResponse:
        """Retrieve semantically relevant context for a query."""
        ...

    async def get_agent_snapshot(
        self,
        session_id: str,
        agent_id: str,
        token_limit: Optional[int] = None,
    ) -> AgentMemorySnapshot:
        """Return a lightweight snapshot of an agent's memory state."""
        ...

    async def list_session_blocks(
        self,
        session_id: str,
        categories: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[SessionBlockSchema]:
        """Return the latest categorical session blocks."""
        ...


# Export all interfaces
__all__ = [
    # Canonical facade (use this)
    "MemoryFacadeInterface",
    # Legacy interfaces (backward compat)
    "MemoryServiceInterface",
    "AgentMemoryServiceInterface",
    "ContextMemoryInterface",
    "VectorMemoryInterface",
]
