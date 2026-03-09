"""Memory Services for MindFlow.

Provides simple and efficient memory storage and retrieval
using SQLite + NumPy for context management.
"""

from __future__ import annotations

from .memory_service import MemoryService, create_memory_service
from .context_storage import ContextStorage
from .context_retriever import ContextRetriever

# Memory service instance
_memory_service = None


def get_memory_service():
    """Get the memory service instance.
    
    Returns:
        MemoryService: The memory service instance
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = create_memory_service()
    return _memory_service

__all__ = [
    "MemoryService",
    "create_memory_service",
    "get_memory_service",
    "ContextStorage",
    "ContextRetriever",
]
