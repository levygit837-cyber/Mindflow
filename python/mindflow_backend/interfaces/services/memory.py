"""Memory service interfaces for MindFlow backend.

This module provides standardized interfaces for memory management services,
including storage, retrieval, and context operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID


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


# Export all interfaces
__all__ = [
    "MemoryServiceInterface",
    "ContextMemoryInterface", 
    "VectorMemoryInterface",
]
