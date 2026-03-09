"""Task RAG Agent interface for real-time context retrieval and semantic memory exchange.

Extends agent contracts with RAG capabilities for Task pipeline components,
enabling semantic context sharing and intelligent dependency resolution.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from mindflow_backend.interfaces.agents.core_personality import (
    CorePersonalityContract,
)

from mindflow_backend.schemas.memory.api import (
    MemorySearchRequest,
    MemorySearchResponse,
    ContextWindowRequest,
    ContextWindowResponse,
)
from mindflow_backend.schemas.agents.research import (
    QueryPlan,
    SearchResult,
)


@runtime_checkable
class TaskRagAgent(CorePersonalityContract, Protocol):
    """Contract for agents with Task RAG capabilities.
    
    Extends core personality capabilities with real-time context retrieval,
    semantic memory exchange, and intelligent task dependency resolution.
    """
    
    async def retrieve_task_context(
        self, 
        request: MemorySearchRequest
    ) -> MemorySearchResponse:
        """Retrieve relevant task context from memory.
        
        Args:
            request: Memory search request with task context
            
        Returns:
            Relevant context for task execution
        """
        ...
    
    async def update_context_window(
        self, 
        request: ContextWindowRequest
    ) -> ContextWindowResponse:
        """Update agent's context window with new information.
        
        Args:
            request: Context window update request
            
        Returns:
            Updated context window status
        """
        ...
    
    async def search_semantic_memory(
        self, 
        query: str, 
        task_id: str | None = None
    ) -> list[SearchResult]:
        """Search semantic memory for relevant information.
        
        Args:
            query: Semantic search query
            task_id: Optional task identifier for context
            
        Returns:
            Relevant semantic memory results
        """
        ...
    
    async def resolve_task_dependencies(
        self, 
        task_id: str, 
        dependency_graph: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve task dependencies using RAG capabilities.
        
        Args:
            task_id: Current task identifier
            dependency_graph: Task dependency structure
            
        Returns:
            Resolved dependencies with context
        """
        ...
    
    async def exchange_context_with_agent(
        self, 
        target_agent_id: str, 
        context_data: dict[str, Any]
    ) -> bool:
        """Exchange context information with another agent.
        
        Args:
            target_agent_id: Target agent identifier
            context_data: Context data to exchange
            
        Returns:
            Success status of context exchange
        """
        ...
