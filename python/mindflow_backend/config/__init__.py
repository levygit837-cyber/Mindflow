"""Configuration management for MindFlow.

Centralized configuration for agents, personalities,
and system-wide settings.
"""

from __future__ import annotations

from .agents import AgentConfig, get_agent_config
from .specialist_rules import SpecialistRuleConfig, get_specialist_rules

__all__ = [
    "AgentConfig",
    "get_agent_config", 
    "SpecialistRuleConfig",
    "get_specialist_rules",
]
