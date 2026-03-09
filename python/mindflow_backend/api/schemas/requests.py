"""Request schemas for API endpoints.

DEPRECATED: This module has been moved to mindflow_backend.schemas.api.requests
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.schemas.api.requests import AgentChatRequest, SessionCreateRequest, SessionUpdateRequest, MessageAddRequest, OrchestrationRequest, TaskDecompositionRequest, SpecialistSelectionRequest, ProviderConfigRequest, ProviderTestRequest, MemorySearchRequest, MemorySummaryRequest, ContextWindowRequest
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.schemas.api.requests import (
    AgentChatRequest,
    SessionCreateRequest,
    SessionUpdateRequest,
    MessageAddRequest,
    OrchestrationRequest,
    TaskDecompositionRequest,
    SpecialistSelectionRequest,
    ProviderConfigRequest,
    ProviderTestRequest,
    MemorySearchRequest,
    MemorySummaryRequest,
    ContextWindowRequest,
)

# Maintain backward compatibility
__all__ = [
    "AgentChatRequest",
    "SessionCreateRequest",
    "SessionUpdateRequest",
    "MessageAddRequest",
    "OrchestrationRequest",
    "TaskDecompositionRequest",
    "SpecialistSelectionRequest",
    "ProviderConfigRequest",
    "ProviderTestRequest",
    "MemorySearchRequest",
    "MemorySummaryRequest",
    "ContextWindowRequest",
]
