"""Interfaces for MindFlow Skills system."""

from .base import (
    SkillInterface,
    SkillLifecycleInterface,
    SkillConfigurableInterface,
    SkillValidatableInterface
)

from .executor import (
    SkillExecutorInterface,
    AsyncSkillExecutorInterface,
    BatchSkillExecutorInterface
)

from .registry import (
    SkillRegistryInterface,
    SkillDiscoveryInterface,
    SkillRecommendationInterface
)

from .specialized import (
    CoreSkillInterface,
    AnalysisSkillInterface,
    CodingSkillInterface,
    ResearchSkillInterface,
    SecuritySkillInterface,
    ArchitectureSkillInterface,
    TestingSkillInterface,
    DocumentationSkillInterface
)

from .lifecycle import (
    SkillManagerInterface,
    SkillOrchestratorInterface,
    SkillMonitoringInterface
)

__all__ = [
    # Base interfaces
    "SkillInterface",
    "SkillLifecycleInterface", 
    "SkillConfigurableInterface",
    "SkillValidatableInterface",
    
    # Executor interfaces
    "SkillExecutorInterface",
    "AsyncSkillExecutorInterface",
    "BatchSkillExecutorInterface",
    
    # Registry interfaces
    "SkillRegistryInterface",
    "SkillDiscoveryInterface",
    "SkillRecommendationInterface",
    
    # Specialized interfaces
    "CoreSkillInterface",
    "AnalysisSkillInterface",
    "CodingSkillInterface",
    "ResearchSkillInterface",
    "SecuritySkillInterface",
    "ArchitectureSkillInterface",
    "TestingSkillInterface",
    "DocumentationSkillInterface",
    
    # Lifecycle interfaces
    "SkillManagerInterface",
    "SkillOrchestratorInterface",
    "SkillMonitoringInterface"
]
