"""Interfaces module for OmniMind agent system.

Provides contracts and protocols for all system components
to ensure loose coupling and testability.
"""

from .core import *
from .agents import *
from .infrastructure import *
from .api import *
from .orchestrator import *

__all__ = [
    # Core interfaces
    "ContextRetriever",
    "VectorStore",
    "Cache",
    "PersonalitySelector",
    "RuleEngine",
    "ContentAnalyzer",
    "ResultParser",
    "Logger",
    "AgentRuntime",
    "AgentFactory",
    "AgentLogBus",
    "SessionManagerContract",
    "StreamingContract",

    # Agent interfaces
    "CorePersonalityContract",
    "EnhancedResearcher",
    "EnhancedCoder",
    "EnhancedAnalyst", 
    "EnhancedReviewer",
    "Analyst",
    "Coder",
    "Reviewer",

    # Infrastructure interfaces
    "BackendProtocol",

    # API interfaces
    "ChatInterface",
    "AgentInterface",

    # Orchestrator interfaces
    "OrchestratorCoreContract",
    "PersonalityManagerContract",
    "DelegationManagerContract",
    
    # Orchestrator Task interfaces
    "TaskerProtocol",
    "SchedulerProtocol",
    "ResolverProtocol",
    "SynthesizerProtocol",
    "ScorerProtocol",
]
