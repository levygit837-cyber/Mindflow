"""Configuration management for OmniMind.

Centralized configuration for agents, personalities,
and system-wide settings.
"""

from __future__ import annotations

from .agents import AgentConfig, get_agent_config
from .personality_rules import PersonalityRuleConfig, get_personality_rules

__all__ = [
    "AgentConfig",
    "get_agent_config", 
    "PersonalityRuleConfig",
    "get_personality_rules",
]
