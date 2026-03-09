"""Service interfaces for MindFlow backend.

Provides contracts and protocols for all service layer components including
communication, monitoring, orchestration, storage, and core services.
"""

from .base import BaseServiceInterface, ServiceLifecycleInterface, CacheableServiceInterface, ConfigurableServiceInterface, BaseAbstractService
from .communication import CommunicationServiceInterface, GrpcServiceInterface, StreamingServiceInterface
from .core import CoreServiceInterface, AgentServiceInterface, SessionServiceInterface, MemoryServiceInterface, ProviderServiceInterface
from .memory import MemoryServiceInterface as MemoryServiceInterfaceNew, ContextMemoryInterface, VectorMemoryInterface
from .monitoring import MonitoringServiceInterface, HealthServiceInterface, MetricsServiceInterface, ReviewServiceInterface
from .orchestration import OrchestrationServiceInterface, TaskServiceInterface, RoutingServiceInterface
from .context import RetrievalServiceInterface as ContextRetrievalServiceInterface, EmbeddingServiceInterface as ContextEmbeddingServiceInterface, VectorStoreInterface as ContextVectorServiceInterface

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
    
    # Monitoring interfaces
    "MonitoringServiceInterface",
    "HealthServiceInterface",
    "MetricsServiceInterface",
    "ReviewServiceInterface",
    
    # Orchestration interfaces
    "OrchestrationServiceInterface",
    "TaskServiceInterface",
    "RoutingServiceInterface",
]
