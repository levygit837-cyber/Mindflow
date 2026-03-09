"""Pydantic schemas for MindFlow Skills system."""

from .base import (
    SkillType,
    SkillCategory,
    SkillStatus,
    SkillPriority,
    SkillMetadata,
    SkillConfiguration,
    SkillInput,
    SkillOutput,
    SkillResult
)

from .core import (
    CoreSkillType,
    AnalysisSkillConfig,
    CodingSkillConfig,
    ResearchSkillConfig
)

from .specialized import (
    SpecializedSkillType,
    SecuritySkillConfig,
    ArchitectureSkillConfig,
    TestingSkillConfig,
    DocumentationSkillConfig
)

from .registry import (
    SkillRegistration,
    SkillDiscovery,
    SkillRegistryEntry,
    SkillQuery,
    SkillFilter
)

from .execution import (
    ExecutionContext,
    ExecutionStatus,
    ExecutionResult,
    SkillExecution,
    ExecutionMetrics,
    PerformanceMetrics
)

__all__ = [
    # Base schemas
    "SkillType",
    "SkillCategory", 
    "SkillStatus",
    "SkillPriority",
    "SkillMetadata",
    "SkillConfiguration",
    "SkillInput",
    "SkillOutput",
    "SkillResult",
    
    # Core schemas
    "CoreSkillType",
    "AnalysisSkillConfig",
    "CodingSkillConfig", 
    "ResearchSkillConfig",
    
    # Specialized schemas
    "SpecializedSkillType",
    "SecuritySkillConfig",
    "ArchitectureSkillConfig",
    "TestingSkillConfig",
    "DocumentationSkillConfig",
    
    # Registry schemas
    "SkillRegistration",
    "SkillDiscovery",
    "SkillRegistryEntry",
    "SkillQuery",
    "SkillFilter",
    
    # Execution schemas
    "ExecutionContext",
    "ExecutionStatus",
    "ExecutionResult",
    "SkillExecution",
    "ExecutionMetrics",
    "PerformanceMetrics"
]
