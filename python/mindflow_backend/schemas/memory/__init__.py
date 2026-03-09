"""Memory schemas for MindFlow backend.

Provides comprehensive schemas for memory operations including contracts,
API schemas, requests, and responses.
"""

from __future__ import annotations

# Core contracts
from .contracts import (
    MemoryType,
    MemoryStatus,
    RetrievalStrategy,
    MemoryEntry,
    ContextWindow,
    MemoryCursor,
    MemoryEvent,
    MemoryFact,
    MemoryEmbedding,
)

# API schemas
from .api import (
    BaseResponse,
    MemorySearchRequest as APIMemorySearchRequest,
    MemorySearchResponse as APIMemorySearchResponse,
    MemorySummaryRequest,
    MemorySummaryResponse,
    ContextWindowRequest as APIContextWindowRequest,
    ContextWindowResponse as APIContextWindowResponse,
    MemoryEventRequest as APIMemoryEventRequest,
    MemoryCursorRequest as APIMemoryCursorRequest,
    MemoryResponse as APIMemoryResponse,
)

# Request schemas
from .requests import (
    MemoryStoreRequest,
    MemoryRetrieveRequest,
    MemorySearchRequest,
    MemoryUpdateRequest,
    MemoryDeleteRequest,
    ContextWindowRequest,
    MemoryCursorRequest as RequestMemoryCursorRequest,
    MemoryStatsRequest,
    MemoryExportRequest,
    MemoryImportRequest,
)

# Response schemas
from .responses import (
    BaseMemoryResponse,
    MemoryStoreResponse,
    MemoryRetrieveResponse,
    MemorySearchResponse,
    SearchResult,
    MemoryUpdateResponse,
    MemoryDeleteResponse,
    ContextWindowResponse,
    MemoryCursorResponse,
    MemoryStatsResponse,
    MemoryExportResponse,
    MemoryImportResponse,
    MemoryBatchResponse,
    MemoryHealthResponse,
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
