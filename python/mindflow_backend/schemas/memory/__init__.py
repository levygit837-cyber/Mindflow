"""Memory schemas for MindFlow backend.

Provides comprehensive schemas for memory operations including contracts,
API schemas, requests, and responses.
"""

from __future__ import annotations

# API schemas
from .api import (
    BaseResponse,
    MemorySummaryRequest,
    MemorySummaryResponse,
)
from .api import (
    ContextWindowRequest as APIContextWindowRequest,
)
from .api import (
    ContextWindowResponse as APIContextWindowResponse,
)
from .api import (
    MemoryCursorRequest as APIMemoryCursorRequest,
)
from .api import (
    MemoryEventRequest as APIMemoryEventRequest,
)
from .api import (
    MemoryResponse as APIMemoryResponse,
)
from .api import (
    MemorySearchRequest as APIMemorySearchRequest,
)
from .api import (
    MemorySearchResponse as APIMemorySearchResponse,
)

# Core contracts
from .contracts import (
    ContextWindow,
    MemoryCursor,
    MemoryEmbedding,
    MemoryEntry,
    MemoryEvent,
    MemoryFact,
    MemoryStatus,
    MemoryType,
    RetrievalStrategy,
)

# Request schemas
from .requests import (
    ContextWindowRequest,
    MemoryDeleteRequest,
    MemoryExportRequest,
    MemoryImportRequest,
    MemoryRetrieveRequest,
    MemorySearchRequest,
    MemoryStatsRequest,
    MemoryStoreRequest,
    MemoryUpdateRequest,
)
from .requests import (
    MemoryCursorRequest as RequestMemoryCursorRequest,
)

# Response schemas
from .responses import (
    BaseMemoryResponse,
    ContextWindowResponse,
    MemoryBatchResponse,
    MemoryCursorResponse,
    MemoryDeleteResponse,
    MemoryExportResponse,
    MemoryHealthResponse,
    MemoryImportResponse,
    MemoryRetrieveResponse,
    MemorySearchResponse,
    MemoryStatsResponse,
    MemoryStoreResponse,
    MemoryUpdateResponse,
    SearchResult,
)

# Export all schemas
__all__ = [
    # Enums and types
    "MemoryType",
    "MemoryStatus",
    "RetrievalStrategy",
    
    # Core contracts
    "MemoryEntry",
    "ContextWindow",
    "MemoryCursor",
    "MemoryEvent",
    "MemoryFact",
    "MemoryEmbedding",
    
    # API schemas
    "BaseResponse",
    "APIMemorySearchRequest",
    "APIMemorySearchResponse",
    "MemorySummaryRequest",
    "MemorySummaryResponse",
    "APIContextWindowRequest",
    "APIContextWindowResponse",
    "APIMemoryEventRequest",
    "APIMemoryCursorRequest",
    "APIMemoryResponse",
    
    # Request schemas
    "MemoryStoreRequest",
    "MemoryRetrieveRequest",
    "MemorySearchRequest",
    "MemoryUpdateRequest",
    "MemoryDeleteRequest",
    "ContextWindowRequest",
    "RequestMemoryCursorRequest",
    "MemoryStatsRequest",
    "MemoryExportRequest",
    "MemoryImportRequest",
    
    # Response schemas
    "BaseMemoryResponse",
    "MemoryStoreResponse",
    "MemoryRetrieveResponse",
    "MemorySearchResponse",
    "SearchResult",
    "MemoryUpdateResponse",
    "MemoryDeleteResponse",
    "ContextWindowResponse",
    "MemoryCursorResponse",
    "MemoryStatsResponse",
    "MemoryExportResponse",
    "MemoryImportResponse",
    "MemoryBatchResponse",
    "MemoryHealthResponse",
]
