"""Re-export shim — tipos canônicos vivem em schemas/memory/contracts.py."""

from mindflow_backend.schemas.memory.contracts import (
    MemoryRetrievalResult,
    MemoryEntry,
    MemoryEvent,
    MemoryCursor,
)

__all__ = [
    "MemoryRetrievalResult",
    "MemoryEntry",
    "MemoryEvent",
    "MemoryCursor",
]
