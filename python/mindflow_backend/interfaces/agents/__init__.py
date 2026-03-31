"""Agent interfaces for MindFlow backend.

Provides contracts and protocols for all agent-related components including
personalities, specialists, enhanced agents, and orchestration.
"""

from ..core.base import AgentInterface
from .analyst import Analyst
from .coder import Coder
from .context import Cache, ContextRetriever, VectorStore
from .core_personality import CorePersonalityContract
from .enhanced_analyst import EnhancedAnalyst
from .enhanced_coder import EnhancedCoder
from .enhanced_reviewer import EnhancedReviewer
from .personality import RuleEngine as PersonalityRuleEngine
from .personality import SpecialistSelector as PersonalitySpecialistSelector
from .researcher import EnhancedResearcher
from .reviewer import Reviewer
from .session import SessionManagerContract
from .specialist import RuleEngine, SpecialistSelector
from .streaming import StreamingContract
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
    "Analyst",
    "Coder",
    "Reviewer",
    "EnhancedCoder",
    "EnhancedAnalyst",
    "EnhancedReviewer",
]
