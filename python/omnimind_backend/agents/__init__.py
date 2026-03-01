"""Agent personality definitions and registry.

Public API:
    - ``BaseAgent`` — immutable agent configuration
    - ``AgentRegistry`` — personality registry singleton
    - ``get_agent`` — retrieve a personality by type
    - ``register_all_personalities`` — startup bootstrap
"""

from omnimind_backend.agents._base import AgentPersonality, BaseAgent
from omnimind_backend.agents._registry import (
    AgentRegistry,
    get_agent,
    get_registry,
    register_all_personalities,
)

__all__ = [
    "AgentPersonality",
    "AgentRegistry",
    "BaseAgent",
    "get_agent",
    "get_registry",
    "register_all_personalities",
]
