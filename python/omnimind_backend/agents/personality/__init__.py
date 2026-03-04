"""Personality system for OmniMind agents.

Unified system that combines prompts and personalities into a single
coherent architecture. The old distinction between prompts/ and personalities/
has been resolved - personalities now contain their own prompts and behaviors.

Key concepts:
- Personalities: Complete agent configurations with prompts, tools, and behaviors
- Sub-personalities: Specialized variants (e.g., security_guard, critic, creative)
- Dynamic prompts: Context-aware prompt generation
- Orchestrator: Decides which personality/sub-personality to use
"""

from __future__ import annotations

# Core personality system
from omnimind_backend.agents.personality.selector import get_personality_selector
from omnimind_backend.agents.personality.configuration import (
    get_personality_config_builder,
    get_delegation_task_builder,
)
from omnimind_backend.agents.personality.rule_engine import get_personality_rule_engine

# Sub-personalities (formerly separate agents)
from omnimind_backend.agents.personality.sub_personalities import (
    SecurityGuardPersonality,
    CriticPersonality,
    CreativePersonality,
    ArchTechPersonality,
    BrainstormPersonality,
    DeepIterationPersonality,
)

# Dynamic prompt system
from omnimind_backend.agents.personality.dynamic_prompts import (
    DynamicPromptBuilder,
    get_dynamic_prompt_builder,
)

__all__ = [
    # Core system
    "get_personality_selector",
    "get_personality_config_builder", 
    "get_delegation_task_builder",
    "get_personality_rule_engine",
    
    # Sub-personalities
    "SecurityGuardPersonality",
    "CriticPersonality", 
    "CreativePersonality",
    "ArchTechPersonality",
    "BrainstormPersonality",
    "DeepIterationPersonality",
    
    # Dynamic prompts
    "DynamicPromptBuilder",
    "get_dynamic_prompt_builder",
]
