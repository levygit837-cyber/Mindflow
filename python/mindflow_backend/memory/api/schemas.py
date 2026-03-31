"""Memory API schemas.

DEPRECATED: This module has been moved to mindflow_backend.schemas.memory.api
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.schemas.memory.api import MemorySearchRequest, MemorySummaryRequest, ContextWindowRequest, MemoryEventRequest, MemoryCursorRequest, MemoryResponse, MemorySearchResponse, MemorySummaryResponse, ContextWindowResponse, BaseResponse
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.schemas.memory.api import (
    BaseResponse,
    ContextWindowRequest,
    ContextWindowResponse,
    MemoryCursorRequest,
    MemoryEventRequest,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySummaryRequest,
    MemorySummaryResponse,
)

# Maintain backward compatibility
__all__ = [
    "MemorySearchRequest",
    "MemorySummaryRequest",
    "ContextWindowRequest",
    "MemoryEventRequest",
    "MemoryCursorRequest",
    "MemoryResponse",
    "MemorySearchResponse",
    "MemorySummaryResponse",
    "ContextWindowResponse",
    "BaseResponse",
]
