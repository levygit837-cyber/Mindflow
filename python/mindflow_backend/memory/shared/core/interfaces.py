"""Re-export shim — interfaces canônicas vivem em interfaces/services/memory.py."""

from mindflow_backend.interfaces.services.memory import AgentMemoryServiceInterface

# Alias backward-compat
MemoryServiceInterface = AgentMemoryServiceInterface

__all__ = ["MemoryServiceInterface", "AgentMemoryServiceInterface"]
