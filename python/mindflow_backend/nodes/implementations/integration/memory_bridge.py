"""Memory Bridge Node - Integrates Nodes with Memory system.

This node provides a clean interface between the Nodes system and the Memory system,
isolating dependencies and maintaining separation of concerns.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.stateful import StatefulNode


class MemoryBridge(StatefulNode, BaseNode):
    """Bridge node for integrating with Memory system.
    
    This node isolates the dependency on the Memory system, providing
    a clean interface for memory operations while maintaining architectural
    separation between Nodes and Memory.
    """
    
    def __init__(
        self,
        node_id: str = "memory_bridge",
        memory_operation: str = "retrieve",  # retrieve, store, search, delete
        max_results: int = 10,
        similarity_threshold: float = 0.7
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PROCESSING,
            category=NodeCategory.INTEGRATION,
            description="Bridge node for memory system integration"
        )
        
        self.memory_operation = memory_operation
        self.max_results = max_results
        self.similarity_threshold = similarity_threshold
        
        # Required inputs vary by operation
        self._setup_required_inputs()
        self.config.outputs = {"result", "metadata", "error"}
        
        # Internal state for memory integration
        self._memory_service = None
    
    def _setup_required_inputs(self) -> None:
        """Setup required inputs based on memory operation."""
        if self.memory_operation == "retrieve":
            self.config.required_inputs = {"session_id", "query"}
        elif self.memory_operation == "store":
            self.config.required_inputs = {"session_id", "content", "metadata"}
        elif self.memory_operation == "search":
            self.config.required_inputs = {"query", "filters"}
        elif self.memory_operation == "delete":
            self.config.required_inputs = {"session_id", "memory_id"}
        else:
            raise ValueError(f"Invalid memory operation: {self.memory_operation}")
    
    async def initialize(self) -> None:
        """Initialize the memory bridge and its dependencies."""
        await super().initialize()
        
        # Import memory dependencies only when needed
        from mindflow_backend.infra.logging import get_logger
        from mindflow_backend.memory import get_memory_service
        
        self._logger = get_logger(__name__)
        
        try:
            # Get memory service
            self._memory_service = await get_memory_service()
            
            self._logger.info("memory_bridge_initialized", 
                           operation=self.memory_operation,
                           max_results=self.max_results,
                           similarity_threshold=self.similarity_threshold)
            
        except Exception as e:
            self._logger.error("memory_bridge_initialization_failed", error=str(e))
            raise
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute memory logic through the bridge interface."""
        if not self._memory_service:
            raise RuntimeError("Memory bridge not properly initialized")
        
        try:
            if self.memory_operation == "retrieve":
                result = await self._retrieve_memory(state)
            elif self.memory_operation == "store":
                result = await self._store_memory(state)
            elif self.memory_operation == "search":
                result = await self._search_memory(state)
            elif self.memory_operation == "delete":
                result = await self._delete_memory(state)
            else:
                raise ValueError(f"Unsupported operation: {self.memory_operation}")
            
            return {
                "result": result["data"],
                "metadata": {
                    "operation": self.memory_operation,
                    "execution_time": result.get("execution_time", 0),
                    "result_count": result.get("count", 0),
                    "success": result.get("success", True),
                },
                "error": None
            }
            
        except Exception as e:
            self._logger.error("memory_bridge_execution_failed", 
                           operation=self.memory_operation,
                           error=str(e))
            
            return {
                "result": None,
                "metadata": {"error_type": type(e).__name__},
                "error": str(e)
            }
    
    async def _retrieve_memory(self, state: dict[str, Any]) -> dict[str, Any]:
        """Retrieve memory content for a session."""
        import time
        
        start_time = time.time()
        session_id = state["session_id"]
        query = state["query"]
        limit = state.get("limit", self.max_results)
        
        # Retrieve context from memory
        memory_result = await self._memory_service.retrieve_context(
            session_id=session_id,
            query=query,
            limit=limit,
            similarity_threshold=self.similarity_threshold
        )
        
        execution_time = time.time() - start_time
        
        return {
            "data": {
                "context": memory_result.context if memory_result else "",
                "memories": memory_result.memories if memory_result else [],
                "session_id": session_id,
                "query": query
            },
            "execution_time": execution_time,
            "count": len(memory_result.memories) if memory_result else 0,
            "success": True
        }
    
    async def _store_memory(self, state: dict[str, Any]) -> dict[str, Any]:
        """Store content in memory."""
        import time
        
        start_time = time.time()
        session_id = state["session_id"]
        content = state["content"]
        metadata = state.get("metadata", {})
        
        # Store in memory
        memory_id = await self._memory_service.store_memory(
            session_id=session_id,
            content=content,
            metadata=metadata
        )
        
        execution_time = time.time() - start_time
        
        return {
            "data": {
                "memory_id": memory_id,
                "session_id": session_id,
                "content": content,
                "metadata": metadata
            },
            "execution_time": execution_time,
            "count": 1,
            "success": True
        }
    
    async def _search_memory(self, state: dict[str, Any]) -> dict[str, Any]:
        """Search memory with filters."""
        import time
        
        start_time = time.time()
        query = state["query"]
        filters = state.get("filters", {})
        limit = state.get("limit", self.max_results)
        
        # Search memory
        search_results = await self._memory_service.search_memory(
            query=query,
            filters=filters,
            limit=limit,
            similarity_threshold=self.similarity_threshold
        )
        
        execution_time = time.time() - start_time
        
        return {
            "data": {
                "results": search_results.results if search_results else [],
                "query": query,
                "filters": filters
            },
            "execution_time": execution_time,
            "count": len(search_results.results) if search_results else 0,
            "success": True
        }
    
    async def _delete_memory(self, state: dict[str, Any]) -> dict[str, Any]:
        """Delete memory entry."""
        import time
        
        start_time = time.time()
        session_id = state["session_id"]
        memory_id = state["memory_id"]
        
        # Delete from memory
        success = await self._memory_service.delete_memory(
            session_id=session_id,
            memory_id=memory_id
        )
        
        execution_time = time.time() - start_time
        
        return {
            "data": {
                "memory_id": memory_id,
                "session_id": session_id,
                "deleted": success
            },
            "execution_time": execution_time,
            "count": 1 if success else 0,
            "success": success
        }
    
    async def get_memory_stats(self, session_id: str) -> dict[str, Any]:
        """Get memory statistics for a session."""
        if not self._memory_service:
            raise RuntimeError("Memory bridge not properly initialized")
        
        try:
            stats = await self._memory_service.get_session_stats(session_id)
            return {
                "session_id": session_id,
                "total_memories": stats.get("total_memories", 0),
                "total_tokens": stats.get("total_tokens", 0),
                "last_access": stats.get("last_access"),
                "oldest_memory": stats.get("oldest_memory"),
                "newest_memory": stats.get("newest_memory"),
            }
        except Exception as e:
            return {
                "session_id": session_id,
                "error": str(e),
                "total_memories": 0
            }
    
    async def clear_session_memory(self, session_id: str) -> dict[str, Any]:
        """Clear all memory for a session."""
        if not self._memory_service:
            raise RuntimeError("Memory bridge not properly initialized")
        
        try:
            deleted_count = await self._memory_service.clear_session(session_id)
            return {
                "session_id": session_id,
                "deleted_count": deleted_count,
                "success": True
            }
        except Exception as e:
            return {
                "session_id": session_id,
                "deleted_count": 0,
                "success": False,
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup memory bridge resources."""
        self._memory_service = None
        
        await super().cleanup()
    
    def update_operation(self, memory_operation: str) -> None:
        """Dynamically update the memory operation."""
        if memory_operation not in ["retrieve", "store", "search", "delete"]:
            raise ValueError(f"Invalid memory operation: {memory_operation}")
        
        self.memory_operation = memory_operation
        self._setup_required_inputs()
