"""Global interfaces for MindFlow backend."""

# Core interfaces
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

# Agent interfaces
from .agents import (
    AgentInterface as AgentsAgentInterface,
    StreamingContract,
    SessionManagerContract,
    Cache,
    SpecialistSelector,
    RuleEngine,
    CorePersonalityContract,
)

# Service layer interfaces
from .services.base import BaseServiceInterface, ServiceLifecycleInterface, CacheableServiceInterface, ConfigurableServiceInterface
from .services.communication import CommunicationServiceInterface, GrpcServiceInterface, StreamingServiceInterface
from .services.context import RetrievalServiceInterface, EmbeddingServiceInterface
from .services.core import CoreServiceInterface, AgentServiceInterface, SessionServiceInterface, MemoryServiceInterface, ProviderServiceInterface
from .services.monitoring import MonitoringServiceInterface, HealthServiceInterface, MetricsServiceInterface
from .services.orchestration import OrchestrationServiceInterface, TaskServiceInterface, RoutingServiceInterface

# API layer interfaces
from .api.controllers import (
    BaseControllerInterface,
    AgentControllerInterface,
    SessionControllerInterface,
    OrchestrationControllerInterface,
    ProviderControllerInterface,
)

# Infrastructure interfaces
from .infrastructure.grpc import GrpcClient, GrpcServer, GrpcConnectionManager
GrpcClientInterface = GrpcClient
GrpcServerInterface = GrpcServer
from .infrastructure.backend import BackendProtocol

# Storage interfaces
from .storage import (
    StorageBackendInterface,
    StorageOperationInterface,
    StorageQueryInterface,
    StorageTransactionInterface,
    StorageIndexInterface,
    StorageBackupInterface,
    StorageMigrationInterface,
    StorageMonitoringInterface,
)

# Storage specialized interfaces
from .storage_specialized.database import DatabaseRepositoryInterface
from .storage_specialized.vector import VectorStoreInterface
from .storage_specialized.cache import CacheManagerInterface
from .storage_specialized.memory import MemoryStoreInterface

# Tool interfaces
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
    PinchTabBrowserHandleInterface,
    PinchTabFleetToolInterface,
    WebhookTool,
    RssFeedTool,
    WebSecurityTool,
)

# Skills interfaces
from .skills import (
    SkillInterface, SkillLifecycleInterface, SkillConfigurableInterface, SkillValidatableInterface,
    SkillExecutorInterface, AsyncSkillExecutorInterface, BatchSkillExecutorInterface,
    SkillRegistryInterface, SkillDiscoveryInterface, SkillRecommendationInterface,
    CoreSkillInterface, AnalysisSkillInterface, CodingSkillInterface, ResearchSkillInterface,
    SecuritySkillInterface, ArchitectureSkillInterface, TestingSkillInterface, DocumentationSkillInterface,
    SkillManagerInterface, SkillOrchestratorInterface, SkillMonitoringInterface,
)
