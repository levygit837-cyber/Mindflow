"""Pydantic schemas for MindFlow Skills system."""

from .base import (
    SkillCategory,
    SkillConfiguration,
    SkillInput,
    SkillMetadata,
    SkillOutput,
    SkillPriority,
    SkillResult,
    SkillStatus,
    SkillType,
)
from .core import AnalysisSkillConfig, CodingSkillConfig, CoreSkillType, ResearchSkillConfig
from .execution import (
    ExecutionContext,
    ExecutionMetrics,
    ExecutionResult,
    ExecutionStatus,
    PerformanceMetrics,
    SkillExecution,
)
from .registry import SkillDiscovery, SkillFilter, SkillQuery, SkillRegistration, SkillRegistryEntry
from .specialized import (
    ArchitectureSkillConfig,
    DocumentationSkillConfig,
    SecuritySkillConfig,
    SpecializedSkillType,
    TestingSkillConfig,
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
