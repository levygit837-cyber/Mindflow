"""Specialized function system prompts.

Context-specific prompts for particular tasks and functions.
These can be combined with core personalities to create specialized behaviors.
"""

from __future__ import annotations

from omnimind_backend.agents.prompts.specialized.agent_delegation import AGENT_DELEGATION_PROMPT
from omnimind_backend.agents.prompts.specialized.architecture_review import (
    ARCHITECTURE_REVIEW_PROMPT,
)
from omnimind_backend.agents.prompts.specialized.brainstorming import BRAINSTORMING_PROMPT
from omnimind_backend.agents.prompts.specialized.code_review import CODE_REVIEW_PROMPT
from omnimind_backend.agents.prompts.specialized.context_governance import CONTEXT_GOVERNANCE_PROMPT
from omnimind_backend.agents.prompts.specialized.deep_analysis import DEEP_ANALYSIS_PROMPT
from omnimind_backend.agents.prompts.specialized.orchestrator_reflection import (
    ORCHESTRATOR_REFLECTION_PROMPT,
)
from omnimind_backend.agents.prompts.specialized.planning import PLANNING_PROMPT

# Specialized functions
from omnimind_backend.agents.prompts.specialized.security_analysis import SECURITY_ANALYSIS_PROMPT

__all__ = [
    "SECURITY_ANALYSIS_PROMPT",
    "ARCHITECTURE_REVIEW_PROMPT",
    "CODE_REVIEW_PROMPT",
    "BRAINSTORMING_PROMPT",
    "DEEP_ANALYSIS_PROMPT",
    "CONTEXT_GOVERNANCE_PROMPT",
    "AGENT_DELEGATION_PROMPT",
    "ORCHESTRATOR_REFLECTION_PROMPT",
    "PLANNING_PROMPT",
]
