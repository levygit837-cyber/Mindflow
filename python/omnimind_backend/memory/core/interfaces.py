"""Memory service interfaces and contracts."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class MemoryServiceInterface(ABC):
    """Interface for memory service operations."""
    
    @abstractmethod
    async def get_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        token_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get agent memory."""
        ...
    
    @abstractmethod
    async def add_memory_event(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int,
        source_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add memory event."""
        ...
    
    @abstractmethod
    async def search_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Search semantic context."""
        ...
    
    @abstractmethod
    async def retrieve_context_for_query(
        self,
        query: str,
        session_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Retrieve context for query."""
        ...
    
    @abstractmethod
    async def create_memory_summary(
        self,
        agent_id: str,
        session_id: str,
        window_range: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Create memory summary."""
        ...
    
    @abstractmethod
    async def get_memory_windows(
        self,
        agent_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get memory windows."""
        ...
    
    @abstractmethod
    async def update_memory_cursor(
        self,
        agent_id: str,
        session_id: str,
        token_total: int,
        tokens_since_summary: int
    ) -> Dict[str, Any]:
        """Update memory cursor."""
        ...
    
    @abstractmethod
    async def initialize_session_memory(self, session_id: str, agent_types: List[str]) -> Dict[str, Any]:
        """Initialize session memory."""
        ...
    
    @abstractmethod
    async def cleanup_session_memory(self, session_id: str) -> bool:
        """Clean up session memory."""
        ...
    
    @abstractmethod
    async def get_session_memory_summary(self, session_id: str) -> Dict[str, Any]:
        """Get session memory summary."""
        ...
