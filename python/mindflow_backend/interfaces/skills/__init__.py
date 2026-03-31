"""Interfaces for MindFlow Skills system."""

from .base import (
    SkillConfigurableInterface,
    SkillInterface,
    SkillLifecycleInterface,
    SkillValidatableInterface,
)
from .executor import (
    AsyncSkillExecutorInterface,
    BatchSkillExecutorInterface,
    SkillExecutorInterface,
)
from .lifecycle import SkillManagerInterface, SkillMonitoringInterface, SkillOrchestratorInterface
from .registry import SkillDiscoveryInterface, SkillRecommendationInterface, SkillRegistryInterface
from .specialized import (
    AnalysisSkillInterface,
    ArchitectureSkillInterface,
    CodingSkillInterface,
    CoreSkillInterface,
    DocumentationSkillInterface,
    ResearchSkillInterface,
    SecuritySkillInterface,
    TestingSkillInterface,
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
