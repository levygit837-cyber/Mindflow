"""Memory domain services for MindFlow backend."""

from __future__ import annotations

from mindflow_backend.services.memory.agent_memory_service import MemoryService
from mindflow_backend.services.memory.memory_facade_service import (
    MemoryFacadeService,
    get_memory_facade_service,
    reset_memory_facade_service,
)
from mindflow_backend.services.memory.memory_service import (
    ContextEntry,
    ContextRetriever,
    ContextStorage,
    MemoryConfig,
    SimpleMemoryService,
    get_simple_memory_service,
)

__all__ = [
    # Main services
    "MemoryService",
    "SimpleMemoryService",
    "MemoryFacadeService",
    # Factory functions
    "get_memory_service",
    "get_simple_memory_service",
    "get_memory_facade_service",
    "reset_memory_facade_service",
    # Legacy/utility classes
    "MemoryConfig",
    "ContextEntry",
    "ContextStorage",
    "ContextRetriever",
]


# Factory function for backward compatibility
def get_memory_service() -> MemoryService:
    """Get the memory service instance."""
    return MemoryService()
