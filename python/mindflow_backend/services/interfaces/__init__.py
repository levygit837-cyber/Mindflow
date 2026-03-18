"""Service interfaces for MindFlow backend.

This module defines contracts and interfaces for all services
to ensure consistency and testability.
"""

from __future__ import annotations

# Import all interface modules
from mindflow_backend.services.interfaces.base_interfaces import (
    BaseServiceInterface,
)

from mindflow_backend.services.interfaces.core_interfaces import (
    AgentServiceInterface,
    SessionServiceInterface,
    MemoryServiceInterface,
    ProviderServiceInterface,
)

from mindflow_backend.services.interfaces.orchestration_interfaces import (
    OrchestrationServiceInterface,
    TaskServiceInterface,
    RoutingServiceInterface,
    TodoPlanningServiceInterface,
)

from mindflow_backend.services.interfaces.context_interfaces import (
    RetrievalServiceInterface,
    EmbeddingServiceInterface,
    VectorStoreInterface,
)

from mindflow_backend.services.interfaces.monitoring_interfaces import (
    HealthServiceInterface,
    MetricsServiceInterface,
    ReviewServiceInterface,
)

from mindflow_backend.services.interfaces.communication_interfaces import (
    GrpcServiceInterface,
    StreamingServiceInterface,
)

# Public exports
__all__ = [
    # Base interfaces
    "BaseServiceInterface",
    
    # Core interfaces
    "AgentServiceInterface",
    "SessionServiceInterface", 
    "MemoryServiceInterface",
    "ProviderServiceInterface",
    
    # Orchestration interfaces
    "OrchestrationServiceInterface",
    "TaskServiceInterface",
    "RoutingServiceInterface",
    "TodoPlanningServiceInterface",
    
    # Context interfaces
    "RetrievalServiceInterface",
    "EmbeddingServiceInterface",
    "VectorStoreInterface",
    
    # Monitoring interfaces
    "HealthServiceInterface",
    "MetricsServiceInterface",
    "ReviewServiceInterface",
    
    # Communication interfaces
    "GrpcServiceInterface",
    "StreamingServiceInterface",
]
