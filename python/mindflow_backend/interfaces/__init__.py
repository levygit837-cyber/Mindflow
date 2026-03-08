"""Global interfaces for MindFlow backend.

This directory contains the centralized interface definitions for the entire MindFlow system,
providing consistency, testability, and maintainability across all components.
"""

# Core interfaces - fundamental for all components
from .core import (
    BaseComponentInterface,
    ServiceInterface,
    AgentInterface,
    ToolInterface,
    InfrastructureInterface,
    LifecycleInterface,
    ConfigurableInterface,
    LoggableInterface,
)

# Agent interfaces - specialized agent contracts
from .agents import (
    AgentInterface,
    StreamingContract,
    SessionManagerContract,
    ContextRetriever,
    VectorStore,
    Cache,
    SpecialistSelector,
    RuleEngine,
)

# Service interfaces - service layer contracts
from .services import (
    BaseServiceInterface,
    ServiceLifecycleInterface,
    CacheableServiceInterface,
    ConfigurableServiceInterface,
    BaseAbstractService,
    CommunicationServiceInterface,
    GrpcServiceInterface,
    StreamingServiceInterface,
    CoreServiceInterface,
    AgentServiceInterface,
    SessionServiceInterface,
    MemoryServiceInterface,
    ProviderServiceInterface,
    MonitoringServiceInterface,
    HealthServiceInterface,
    MetricsServiceInterface,
    ReviewServiceInterface,
    OrchestrationServiceInterface,
    TaskServiceInterface,
    RoutingServiceInterface,
)

# API interfaces - API layer contracts
from .api import (
    AgentControllerInterface,
    SessionControllerInterface,
    OrchestrationControllerInterface,
    ProviderControllerInterface,
    MemoryControllerInterface,
    BaseControllerInterface,
)

# Infrastructure interfaces - infrastructure component contracts
from .infrastructure import (
    GrpcClient,
    GrpcServer,
    GrpcConnectionManager,
)

# Tool interfaces - agent tool contracts
from .tools import (
    ToolInterface as ToolBaseInterface,
    AsyncToolInterface,
    StatefulToolInterface,
    ToolSchema,
    ToolPermission,
    FileReadTool,
    FileWriteTool,
    FileEditTool,
    DirectoryListTool,
    FileDeleteTool,
    DirectoryCreateTool,
    GrepSearchTool,
    GlobSearchTool,
    FindFilesTool,
    SystemToolInterface,
    ProcessManagerTool,
    SandboxTool,
    SystemMonitorTool,
    EnvironmentTool,
    PermissionTool,
    WebToolInterface,
    HttpClientTool,
    ApiClientTool,
    BrowserSearchTool,
    WebhookTool,
    RssFeedTool,
    WebSecurityTool,
)

__all__ = [
    # Core interfaces
    "BaseComponentInterface",
    "ServiceInterface",
    "AgentInterface",
    "ToolInterface",
    "InfrastructureInterface",
    "LifecycleInterface",
    "ConfigurableInterface",
    "LoggableInterface",
    
    # Agent interfaces
    "AgentInterface",
    "StreamingContract",
    "SessionManagerContract",
    "ContextRetriever",
    "VectorStore",
    "Cache",
    "SpecialistSelector",
    "RuleEngine",
    
    # Service interfaces
    "BaseServiceInterface",
    "ServiceLifecycleInterface",
    "CacheableServiceInterface",
    "ConfigurableServiceInterface",
    "BaseAbstractService",
    "CommunicationServiceInterface",
    "GrpcServiceInterface",
    "StreamingServiceInterface",
    "CoreServiceInterface",
    "AgentServiceInterface",
    "SessionServiceInterface",
    "MemoryServiceInterface",
    "ProviderServiceInterface",
    "MonitoringServiceInterface",
    "HealthServiceInterface",
    "MetricsServiceInterface",
    "ReviewServiceInterface",
    "OrchestrationServiceInterface",
    "TaskServiceInterface",
    "RoutingServiceInterface",
    
    # API interfaces
    "AgentControllerInterface",
    "SessionControllerInterface",
    "OrchestrationControllerInterface",
    "ProviderControllerInterface",
    "MemoryControllerInterface",
    "BaseControllerInterface",
    
    # Infrastructure interfaces
    "GrpcClient",
    "GrpcServer",
    "GrpcConnectionManager",
    
    # Tool interfaces
    "ToolBaseInterface",
    "AsyncToolInterface",
    "StatefulToolInterface",
    "ToolSchema",
    "ToolPermission",
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "DirectoryListTool",
    "FileDeleteTool",
    "DirectoryCreateTool",
    "GrepSearchTool",
    "GlobSearchTool",
    "FindFilesTool",
    "SystemToolInterface",
    "ProcessManagerTool",
    "SandboxTool",
    "SystemMonitorTool",
    "EnvironmentTool",
    "PermissionTool",
    "WebToolInterface",
    "HttpClientTool",
    "ApiClientTool",
    "BrowserSearchTool",
    "WebhookTool",
    "RssFeedTool",
    "WebSecurityTool",
]
