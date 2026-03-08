"""MindFlow Backend Services.

This module provides a unified interface for all business services
in the MindFlow backend, organized by domain and functionality.

Services are organized into the following domains:
- core: Fundamental business services (agents, sessions, memory, providers)
- orchestration: Task decomposition and agent coordination
- context: Semantic context retrieval and vector management
- monitoring: Health checks, metrics, and session review
- communication: gRPC and streaming services
- interfaces: Service contracts and base interfaces

Usage:
    # Get services using factory functions
    from mindflow_backend.services import get_agent_service
    
    agent_service = get_agent_service()
    result = await agent_service.process_agent_request(...)
    
    # Or use dependency injection container
    from mindflow_backend.services.core.container import get_service
    
    agent_service = get_service("agent_service")
"""

from __future__ import annotations

# Core domain services
from mindflow_backend.services.core import (
    get_agent_service,
    get_session_service,
    get_provider_service,
)

# Orchestration domain services
from mindflow_backend.services.orchestration import (
    get_orchestration_service,
    get_task_service,
    get_routing_service,
)

# Context domain services
from mindflow_backend.services.context import (
    get_retrieval_service,
    get_embedding_service,
    get_vector_service,
)

# Monitoring domain services
from mindflow_backend.services.monitoring import (
    get_health_service,
    get_metrics_service,
    get_review_service,
)

# Communication domain services
from mindflow_backend.services.communication import (
    get_grpc_service,
    get_streaming_service,
)

# Dependency injection container
from mindflow_backend.services.core.container import (
    get_container,
    get_service,
    register_service,
    initialize_core_services,
)

# Service interfaces
from mindflow_backend.services.interfaces import (
    BaseServiceInterface,
    AgentServiceInterface,
    SessionServiceInterface,
    MemoryServiceInterface,
    ProviderServiceInterface,
    OrchestrationServiceInterface,
    TaskServiceInterface,
    RoutingServiceInterface,
    RetrievalServiceInterface,
    EmbeddingServiceInterface,
    VectorServiceInterface,
    HealthServiceInterface,
    MetricsServiceInterface,
    ReviewServiceInterface,
    GrpcServiceInterface,
    StreamingServiceInterface,
)

# Public API - factory functions for all services
__all__ = [
    # Core services
    "get_agent_service",
    "get_session_service",
    "get_provider_service",
    
    # Orchestration services
    "get_orchestration_service",
    "get_task_service",
    "get_routing_service",
    
    # Context services
    "get_retrieval_service",
    "get_embedding_service",
    "get_vector_service",
    
    # Monitoring services
    "get_health_service",
    "get_metrics_service",
    "get_review_service",
    
    # Communication services
    "get_grpc_service",
    "get_streaming_service",
    
    # Dependency injection
    "get_container",
    "get_service",
    "register_service",
    "initialize_core_services",
    
    # Interfaces
    "BaseServiceInterface",
    "AgentServiceInterface",
    "SessionServiceInterface",
    "MemoryServiceInterface",
    "ProviderServiceInterface",
    "OrchestrationServiceInterface",
    "TaskServiceInterface",
    "RoutingServiceInterface",
    "RetrievalServiceInterface",
    "EmbeddingServiceInterface",
    "VectorServiceInterface",
    "HealthServiceInterface",
    "MetricsServiceInterface",
    "ReviewServiceInterface",
    "GrpcServiceInterface",
    "StreamingServiceInterface",
]

# Initialize core services on import
try:
    initialize_core_services()
except Exception:
    # Silently fail during import - services will be initialized on first use
    pass
