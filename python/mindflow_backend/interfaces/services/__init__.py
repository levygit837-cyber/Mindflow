"""Service interfaces for MindFlow backend.

Provides contracts and protocols for all service layer components including
communication, monitoring, orchestration, storage, and core services.
"""

from .base import (
    BaseAbstractService,
    BaseServiceInterface,
    CacheableServiceInterface,
    ConfigurableServiceInterface,
    ServiceLifecycleInterface,
)
from .communication import (
    CommunicationServiceInterface,
    GrpcServiceInterface,
    StreamingServiceInterface,
)
from .context import EmbeddingServiceInterface as ContextEmbeddingServiceInterface
from .context import RetrievalServiceInterface as ContextRetrievalServiceInterface
from .context import VectorStoreInterface as ContextVectorServiceInterface
from .core import (
    AgentServiceInterface,
    CoreServiceInterface,
    MemoryServiceInterface,
    ProviderServiceInterface,
    SessionServiceInterface,
)
from .memory import ContextMemoryInterface, VectorMemoryInterface
from .memory import MemoryServiceInterface as MemoryServiceInterfaceNew
from .monitoring import (
    HealthServiceInterface,
    MetricsServiceInterface,
    MonitoringServiceInterface,
    ReviewServiceInterface,
)
from .orchestration import (
    OrchestrationServiceInterface,
    RoutingServiceInterface,
    TaskServiceInterface,
    TodoPlanningServiceInterface,
)
from .pinchtab import (
    PinchTabBrowserServiceInterface,
    PinchTabContainerOrchestratorInterface,
    PinchTabFleetServiceInterface,
)

__all__ = [
    # Base service interfaces
    "BaseServiceInterface",
    "ServiceLifecycleInterface",
    "CacheableServiceInterface",
    "ConfigurableServiceInterface",
    "BaseAbstractService",
    
    # Communication interfaces
    "CommunicationServiceInterface",
    "GrpcServiceInterface",
    "StreamingServiceInterface",
    
    # Core service interfaces
    "CoreServiceInterface",
    "AgentServiceInterface",
    "SessionServiceInterface",
    "MemoryServiceInterface",
    "MemoryServiceInterfaceNew",
    "ContextMemoryInterface",
    "VectorMemoryInterface",
    "ProviderServiceInterface",
    
    # Context service interfaces
    "ContextRetrievalServiceInterface",
    "ContextEmbeddingServiceInterface",
    "ContextVectorServiceInterface",
    "PinchTabBrowserServiceInterface",
    "PinchTabContainerOrchestratorInterface",
    "PinchTabFleetServiceInterface",
    
    # Monitoring interfaces
    "MonitoringServiceInterface",
    "HealthServiceInterface",
    "MetricsServiceInterface",
    "ReviewServiceInterface",
    
    # Orchestration interfaces
    "OrchestrationServiceInterface",
    "TaskServiceInterface",
    "RoutingServiceInterface",
    "TodoPlanningServiceInterface",
]
