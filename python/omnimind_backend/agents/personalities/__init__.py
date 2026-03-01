"""Agent personality factories.

Re-exports all ``create_*_agent()`` factory functions.
"""

from omnimind_backend.agents.personalities.analyst import create_analyst_agent
from omnimind_backend.agents.personalities.arch_tech import create_arch_tech_agent
from omnimind_backend.agents.personalities.coder import create_coder_agent
from omnimind_backend.agents.personalities.critic import create_critic_agent
from omnimind_backend.agents.personalities.researcher import create_researcher_agent

__all__ = [
    "create_analyst_agent",
    "create_arch_tech_agent",
    "create_coder_agent",
    "create_critic_agent",
    "create_researcher_agent",
]
