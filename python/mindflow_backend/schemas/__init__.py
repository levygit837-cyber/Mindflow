"""Pydantic schemas for MindFlow backend contracts."""

# Core imports
# Agent schemas
from .agents.analyst import AnalysisMode, AnalystOutput
from .agents.research import IterationType, QuestionType, SourceType
from .agents.security_guard import Exploitability, RemediationPriority, Severity

# Chat schemas
from .chat.agent import (
    AgentChatRequest,
    ChatMessageSchema,
    ChatSessionSchema,
    NotifierPayload,
    StreamEvent,
)
from .config.normalization import NormalizationConfig

# Config schemas
from .config.settings import AppSettings, SettingsUpdate
from .core.common import LLMProvider

# Memory schemas
from .memory import (
    ContextWindow,
    MemoryCursor,
    MemoryEmbedding,
    MemoryEntry,
    MemoryEvent,
    MemoryFact,
    MemoryRetrieveRequest,
    MemoryRetrieveResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStatus,
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemoryType,
    RetrievalStrategy,
)
from .orchestration.delegation import AgentSessionStatus, ContextContinuity, DelegationStatus

# Orchestration schemas
from .orchestration.orchestrator import AgentType, ThinkingLevel, ThinkingMode, ToolScope
from .orchestration.specialists import SpecialistType, SpecializationRequirement, TaskComplexity
from .session.chunk import ChunkEdgeType, ChunkType

# Session schemas
from .session.contracts import RelationshipType, RetrievalMode, SessionMode
from .session.governance import ContextScope

# Skills schemas
from .skills import (
    AnalysisSkillConfig,
    ArchitectureSkillConfig,
    CodingSkillConfig,
    # Core schemas
    CoreSkillType,
    DocumentationSkillConfig,
    # Execution schemas
    ExecutionContext,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionStatus,
    PerformanceMetrics,
    ResearchSkillConfig,
    SecuritySkillConfig,
    SkillCategory,
    SkillConfiguration,
    SkillDiscovery,
    SkillExecution,
    SkillFilter,
    SkillInput,
    SkillMetadata,
    SkillOutput,
    SkillPriority,
    SkillQuery,
    # Registry schemas
    SkillRegistration,
    SkillRegistryEntry,
    SkillResult,
    SkillStatus,
    # Base schemas
    SkillType,
    # Specialized schemas
    SpecializedSkillType,
    TestingSkillConfig,
)

# Storage schemas (NEW)
from .storage import (
    StorageBackup,
    StorageConfig,
    StorageHealthCheck,
    StorageMigration,
    StorageOperation,
    StorageRequest,
    StorageResponse,
    StorageStats,
    StorageType,
)
from .storage_specialized.cache import CacheConfig, CacheEntry, CacheStats

# Storage specialized schemas
from .storage_specialized.database import (
    ConnectionConfig,
    DatabaseType,
    HealthCheckConfig,
    MigrationConfig,
    PoolConfig,
)
from .storage_specialized.memory import StorageMemoryEntry, StorageMemoryStats, StorageMemoryWindow
from .storage_specialized.vector import (
    VectorCollection,
    VectorConfig,
    VectorMetadata,
    VectorSearchRequest,
    VectorSearchResponse,
)

__all__ = [
    # Core
    "LLMProvider",
    
    # Agents
    "AnalysisMode", "AnalystOutput",
    "IterationType", "SourceType", "QuestionType",
    "Severity", "Exploitability", "RemediationPriority",
    
    # Orchestration
    "AgentType", "ThinkingLevel", "ThinkingMode", "ToolScope",
    "DelegationStatus", "ContextContinuity", "AgentSessionStatus",
    "SpecialistType", "TaskComplexity", "SpecializationRequirement",
    
    # Session
    "SessionMode", "RelationshipType", "RetrievalMode",
    "ChunkType", "ChunkEdgeType",
    "ContextScope",
    
    # Chat
    "AgentChatRequest", "ChatMessageSchema", "ChatSessionSchema", "NotifierPayload", "StreamEvent",
    
    # Config
    "AppSettings", "SettingsUpdate", "NormalizationConfig",
    
    # Memory
    "MemoryType", "MemoryStatus", "RetrievalStrategy",
    "MemoryEntry", "ContextWindow", "MemoryCursor", "MemoryEvent",
    "MemoryFact", "MemoryEmbedding",
    "MemoryStoreRequest", "MemoryRetrieveRequest", "MemorySearchRequest",
    "MemoryStoreResponse", "MemoryRetrieveResponse", "MemorySearchResponse",
    
    # Storage (NEW)
    "StorageType", "StorageConfig", "StorageOperation", "StorageStats",
    "StorageHealthCheck", "StorageMigration", "StorageBackup",
    "StorageRequest", "StorageResponse",
    
    # Skills
    # Base schemas
    "SkillType", "SkillCategory", "SkillStatus", "SkillPriority", "SkillMetadata", "SkillConfiguration", "SkillInput", "SkillOutput", "SkillResult",
    # Core schemas
    "CoreSkillType", "AnalysisSkillConfig", "CodingSkillConfig", "ResearchSkillConfig",
    # Specialized schemas
    "SpecializedSkillType", "SecuritySkillConfig", "ArchitectureSkillConfig", "TestingSkillConfig", "DocumentationSkillConfig",
    # Registry schemas
    "SkillRegistration", "SkillDiscovery", "SkillRegistryEntry", "SkillQuery", "SkillFilter",
    # Execution schemas
    "ExecutionContext", "ExecutionStatus", "ExecutionResult", "SkillExecution", "ExecutionMetrics", "PerformanceMetrics",
]
