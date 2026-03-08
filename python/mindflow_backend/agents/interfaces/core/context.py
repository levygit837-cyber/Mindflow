"""Context management interfaces.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.context
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import ContextRetriever, VectorStore, Cache
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.agents.context import ContextRetriever, VectorStore, Cache

# Maintain backward compatibility
__all__ = ["ContextRetriever", "VectorStore", "Cache"]
