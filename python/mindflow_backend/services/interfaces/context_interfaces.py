"""Context service interfaces for MindFlow backend.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.services.context
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.services import RetrievalServiceInterface, EmbeddingServiceInterface, VectorStoreInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.services.context import (
    EmbeddingServiceInterface,
    RetrievalServiceInterface,
    VectorStoreInterface,
)

# Maintain backward compatibility
__all__ = [
    "RetrievalServiceInterface",
    "EmbeddingServiceInterface",
    "VectorStoreInterface",
]
