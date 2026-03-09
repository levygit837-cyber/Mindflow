"""Pydantic schemas for MindFlow backend contracts."""

# Core imports
from .core.common import LLMProvider

# Agent schemas
from .agents.analyst import AnalysisMode, AnalystOutput
from .agents.creative import CreativeWorkType, PathEvaluation
from .agents.research import IterationType, SourceType, QuestionType
from .agents.security_guard import Severity, Exploitability, RemediationPriority

# Orchestration schemas
from .orchestration.orchestrator import AgentType, ThinkingLevel, ThinkingMode, ToolScope
from .orchestration.delegation import DelegationStatus, ContextContinuity, AgentSessionStatus
from .orchestration.specialists import SpecialistType, TaskComplexity, SpecializationRequirement

# Session schemas
from .session.contracts import SessionMode, RelationshipType, RetrievalMode
from .session.chunk import ChunkType, ChunkEdgeType
from .session.governance import ContextScope

# Chat schemas
from .chat.agent import AgentChatRequest, ChatMessageSchema, ChatSessionSchema, NotifierPayload, StreamEvent

# Config schemas
from .config.settings import AppSettings, SettingsUpdate
from .config.normalization import NormalizationConfig

# Memory schemas
from .memory import (
    MemoryType, MemoryStatus, RetrievalStrategy,
    MemoryEntry, ContextWindow, MemoryCursor, MemoryEvent,
    MemoryFact, MemoryEmbedding,
    MemoryStoreRequest, MemoryRetrieveRequest, MemorySearchRequest,
    MemoryStoreResponse, MemoryRetrieveResponse, MemorySearchResponse,
)

# Skills schemas
from .skills import (
    # Base schemas
    SkillType, SkillCategory, SkillStatus, SkillPriority, SkillMetadata, SkillConfiguration, SkillInput, SkillOutput, SkillResult,
    # Core schemas
    CoreSkillType, AnalysisSkillConfig, CodingSkillConfig, ResearchSkillConfig,
    # Specialized schemas
    SpecializedSkillType, SecuritySkillConfig, ArchitectureSkillConfig, TestingSkillConfig, DocumentationSkillConfig,
    # Registry schemas
    SkillRegistration, SkillDiscovery, SkillRegistryEntry, SkillQuery, SkillFilter,
    # Execution schemas
    ExecutionContext, ExecutionStatus, ExecutionResult, SkillExecution, ExecutionMetrics, PerformanceMetrics
)

__all__ = [
    # Core
    "LLMProvider",
    
    # Agents
    "AnalysisMode", "AnalystOutput",
    "CreativeWorkType", "PathEvaluation", 
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
