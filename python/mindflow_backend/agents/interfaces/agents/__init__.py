"""Agent-specific interfaces.

Provides contracts for specialized agent implementations
including researcher, analyst, coder, and reviewer agents,
with enhanced versions and core personality contract.
"""

from .core_personality import CorePersonalityContract
from .researcher import EnhancedResearcher
from .analyst import Analyst
from .coder import Coder
from .reviewer import Reviewer
from .enhanced_coder import EnhancedCoder
from .enhanced_analyst import EnhancedAnalyst
from .enhanced_reviewer import EnhancedReviewer

__all__ = [
    "CorePersonalityContract",
    "EnhancedResearcher",
    "Analyst", 
    "Coder",
    "Reviewer",
    "EnhancedCoder",
    "EnhancedAnalyst",
    "EnhancedReviewer",
]
