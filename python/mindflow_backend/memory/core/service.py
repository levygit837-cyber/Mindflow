"""Memory service for managing agent memory, context windows, and RAG operations.

DEPRECATED: This module has been moved to mindflow_backend.services.memory.agent_memory_service
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services.memory import get_memory_service
"""

# Forward compatibility alias - import from centralized location
from mindflow_backend.services.memory.agent_memory_service import MemoryService

# Maintain backward compatibility
__all__ = ["MemoryService"]
