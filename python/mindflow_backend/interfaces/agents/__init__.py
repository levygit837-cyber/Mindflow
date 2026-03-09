"""Agent interfaces for MindFlow backend.

Provides contracts and protocols for all agent-related components including
personalities, specialists, enhanced agents, and orchestration.
"""

from ..core.base import AgentInterface
from .streaming import StreamingContract
from .session import SessionManagerContract
from .context import ContextRetriever, VectorStore, Cache
from .specialist import SpecialistSelector, RuleEngine
from .core_personality import CorePersonalityContract
from .personality import SpecialistSelector as PersonalitySpecialistSelector, RuleEngine as PersonalityRuleEngine
from .researcher import EnhancedResearcher
from .task_rag_agent import TaskRagAgent

__all__ = [
    # Core agent contracts
    "AgentInterface",
    "StreamingContract",
    "SessionManagerContract",
    
    # Context and infrastructure
    "ContextRetriever",
    "VectorStore", 
    "Cache",
    
    # Selection and management
    "SpecialistSelector",
    "RuleEngine",
    
    # Enhanced agent contracts
    "CorePersonalityContract",
    "PersonalitySpecialistSelector",
    "PersonalityRuleEngine",
    "EnhancedResearcher",
    "TaskRagAgent",
]
