"""Agent prompt definitions.

Re-exports all personality system prompts for convenient access.
"""

from omnimind_backend.agents.prompts.analyst import ANALYST_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.arch_tech import ARCH_TECH_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.base import OMNIMIND_PREAMBLE, build_system_prompt
from omnimind_backend.agents.prompts.coder import CODER_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.creative import CREATIVE_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.critic import CRITIC_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.researcher import RESEARCHER_SYSTEM_PROMPT
from omnimind_backend.agents.prompts.security_guard import SECURITY_GUARD_SYSTEM_PROMPT

__all__ = [
    "ANALYST_SYSTEM_PROMPT",
    "ARCH_TECH_SYSTEM_PROMPT",
    "CODER_SYSTEM_PROMPT",
    "CREATIVE_SYSTEM_PROMPT",
    "CRITIC_SYSTEM_PROMPT",
    "OMNIMIND_PREAMBLE",
    "RESEARCHER_SYSTEM_PROMPT",
    "SECURITY_GUARD_SYSTEM_PROMPT",
    "build_system_prompt",
]
