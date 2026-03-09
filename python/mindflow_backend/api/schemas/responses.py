"""Response schemas for API endpoints.

DEPRECATED: This module has been moved to mindflow_backend.schemas.api.responses
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.schemas.api.responses import AgentResponse, SessionResponse, MessageResponse, SessionListResponse, OrchestrationResponse, TaskDecompositionResponse, SpecialistSelectionResponse, ProviderResponse, ProviderListResponse, ProviderTestResponse, MemoryResponse, MemorySearchResponse, MemorySummaryResponse, ContextWindowResponse, ExecutionStatusResponse, FallbackResponse
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.schemas.api.responses import (
    AgentResponse,
    SessionResponse,
    MessageResponse,
    SessionListResponse,
    OrchestrationResponse,
    TaskDecompositionResponse,
    SpecialistSelectionResponse,
    ProviderResponse,
    ProviderListResponse,
    ProviderTestResponse,
    MemoryResponse,
    MemorySearchResponse,
    MemorySummaryResponse,
    ContextWindowResponse,
    ExecutionStatusResponse,
    FallbackResponse,
)

# Maintain backward compatibility
__all__ = [
    "AgentResponse",
    "SessionResponse",
    "MessageResponse",
    "SessionListResponse",
    "OrchestrationResponse",
    "TaskDecompositionResponse",
    "SpecialistSelectionResponse",
    "ProviderResponse",
    "ProviderListResponse",
    "ProviderTestResponse",
    "MemoryResponse",
    "MemorySearchResponse",
    "MemorySummaryResponse",
    "ContextWindowResponse",
    "ExecutionStatusResponse",
    "FallbackResponse",
]
