"""Service interfaces for MindFlow backend.

Provides contracts and protocols for all service layer components including
communication, monitoring, orchestration, storage, and core services.
"""

from .base import BaseServiceInterface, ServiceLifecycleInterface, CacheableServiceInterface, ConfigurableServiceInterface, BaseAbstractService
from .communication import CommunicationServiceInterface, GrpcServiceInterface, StreamingServiceInterface
from .core import CoreServiceInterface, AgentServiceInterface, SessionServiceInterface, MemoryServiceInterface, ProviderServiceInterface
from .monitoring import MonitoringServiceInterface, HealthServiceInterface, MetricsServiceInterface, ReviewServiceInterface
from .orchestration import OrchestrationServiceInterface, TaskServiceInterface, RoutingServiceInterface

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
    "ProviderServiceInterface",
    
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
