"""Core personality system prompts.

Primary agent personalities with their essential protocols and behaviors.
These are the foundational prompts that define each agent's core identity.
"""

from __future__ import annotations

# Core personalities
from omnimind_backend.agents.prompts.core.analyst import ANALYST_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.core.coder import CODER_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.core.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.core.researcher import RESEARCHER_SYSTEM_PROMPT

__all__ = [
    "ANALYST_SYSTEM_PROMPT",
    "CODER_SYSTEM_PROMPT", 
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "RESEARCHER_SYSTEM_PROMPT",
]
