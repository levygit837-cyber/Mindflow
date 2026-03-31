"""Global interfaces for MindFlow backend."""

# Core interfaces
# Agent interfaces
from .agents import (
    AgentInterface as AgentsAgentInterface,
)
from .agents import (
    Cache,
    CorePersonalityContract,
    RuleEngine,
    SessionManagerContract,
    SpecialistSelector,
    StreamingContract,
)

# API layer interfaces
from .api.controllers import (
    AgentControllerInterface,
    BaseControllerInterface,
    OrchestrationControllerInterface,
    ProviderControllerInterface,
    SessionControllerInterface,
)
from .core import (
    AgentInterface,
    BaseComponentInterface,
    ConfigurableInterface,
    InfrastructureInterface,
    LifecycleInterface,
    LoggableInterface,
    ServiceInterface,
    ToolInterface,
)

# Infrastructure interfaces
from .infrastructure.grpc import GrpcClient, GrpcConnectionManager, GrpcServer

# Orchestrator interfaces
from .orchestrator import (
    DelegationManagerContract,
    OrchestratorCoreContract,
    PersonalityManagerContract,
    ResolverProtocol,
    SchedulerProtocol,
    ScorerProtocol,
    SynthesizerProtocol,
    TaskerProtocol,
)

# Service layer interfaces
from .services.base import (
    BaseServiceInterface,
    CacheableServiceInterface,
    ConfigurableServiceInterface,
    ServiceLifecycleInterface,
)
from .services.communication import (
    CommunicationServiceInterface,
    GrpcServiceInterface,
    StreamingServiceInterface,
)
from .services.context import EmbeddingServiceInterface, RetrievalServiceInterface
from .services.core import (
    AgentServiceInterface,
    CoreServiceInterface,
    MemoryServiceInterface,
    ProviderServiceInterface,
    SessionServiceInterface,
)
from .services.monitoring import (
    HealthServiceInterface,
    MetricsServiceInterface,
    MonitoringServiceInterface,
)
from .services.orchestration import (
    OrchestrationServiceInterface,
    RoutingServiceInterface,
    TaskServiceInterface,
)

GrpcClientInterface = GrpcClient
GrpcServerInterface = GrpcServer
from .infrastructure.backend import BackendProtocol

# Skills interfaces
from .skills import (
    AnalysisSkillInterface,
    ArchitectureSkillInterface,
    AsyncSkillExecutorInterface,
    BatchSkillExecutorInterface,
    CodingSkillInterface,
    CoreSkillInterface,
    DocumentationSkillInterface,
    ResearchSkillInterface,
    SecuritySkillInterface,
    SkillConfigurableInterface,
    SkillDiscoveryInterface,
    SkillExecutorInterface,
    SkillInterface,
    SkillLifecycleInterface,
    SkillManagerInterface,
    SkillMonitoringInterface,
    SkillOrchestratorInterface,
    SkillRecommendationInterface,
    SkillRegistryInterface,
    SkillValidatableInterface,
    TestingSkillInterface,
)

# Storage interfaces
from .storage import (
    StorageBackendInterface,
    StorageBackupInterface,
    StorageIndexInterface,
    StorageMigrationInterface,
    StorageMonitoringInterface,
    StorageOperationInterface,
    StorageQueryInterface,
    StorageTransactionInterface,
)
from .storage_specialized.cache import CacheManagerInterface

# Storage specialized interfaces
from .storage_specialized.database import DatabaseRepositoryInterface
from .storage_specialized.memory import MemoryStoreInterface
from .storage_specialized.vector import VectorStoreInterface
from .tools import (
    ApiClientTool,
    AsyncToolInterface,
    BrowserSearchTool,
    DirectoryCreateTool,
    DirectoryListTool,
    EnvironmentTool,
    FileDeleteTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    FindFilesTool,
    GlobSearchTool,
    GrepSearchTool,
    HttpClientTool,
    PermissionTool,
    PinchTabBrowserHandleInterface,
    PinchTabFleetToolInterface,
    ProcessManagerTool,
    RssFeedTool,
    SandboxTool,
    StatefulToolInterface,
    SystemMonitorTool,
    SystemToolInterface,
    ToolPermission,
    ToolSchema,
    WebhookTool,
    WebSecurityTool,
    WebToolInterface,
)

# Tool interfaces
from .tools import (
    ToolInterface as ToolBaseInterface,
)
