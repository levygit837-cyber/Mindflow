"""Specialist system for MindFlow agents.

Unified system that combines prompts and specialists into a single
coherent architecture. The old distinction between prompts/ and personalities/
has been resolved - specialists now contain their own prompts and behaviors.

Key concepts:
- Specialists: Complete agent configurations with prompts, tools, and behaviors
- Specialized variants: Specialized variants (e.g., security_guard, critic, creative)
- Dynamic prompts: Context-aware prompt generation
- Orchestrator: Decides which specialist to use
"""

from __future__ import annotations

# Core specialist system
from mindflow_backend.agents.specialists.selector import get_specialist_selector
from mindflow_backend.agents.specialists.configuration import (
    get_specialist_config_builder,
    get_delegation_task_builder,
)
from mindflow_backend.agents.specialists.rule_engine import get_specialist_rule_engine

# Specialists (formerly separate agents)
from mindflow_backend.agents.specialists.specialists import (
    SecuritySpecialist,
    ReviewSpecialist,
    CreativeSpecialist,
    ArchitectureSpecialist,
    BrainstormSpecialist,
    DeepAnalysisSpecialist,
)

# Agent factories (migrated from personalities)
from mindflow_backend.agents.specialists.factories import (
    create_analyst_agent,
    create_coder_agent,
    create_researcher_agent,
    create_orchestrator_agent,
    create_security_agent,
    create_review_agent,
    create_architecture_agent,
    create_creative_agent,
    create_deep_analysis_agent,
    ANALYST_SUB_PERSONALITIES,
    CODER_SUB_PERSONALITIES,
)

# Dynamic prompt system
from mindflow_backend.agents.specialists.dynamic_prompts import (
    DynamicPromptBuilder,
    get_dynamic_prompt_builder,
)

__all__ = [
    # Core system
    "get_specialist_selector",
    "get_specialist_config_builder", 
    "get_delegation_task_builder",
    "get_specialist_rule_engine",
    
    # Specialists
    "SecuritySpecialist",
    "ReviewSpecialist", 
    "CreativeSpecialist",
    "ArchitectureSpecialist",
    "BrainstormSpecialist",
    "DeepAnalysisSpecialist",
    
    # Agent factories (migrated from personalities)
    "create_analyst_agent",
    "create_coder_agent",
    "create_researcher_agent",
    "create_orchestrator_agent",
    "create_security_agent",
    "create_review_agent",
    "create_architecture_agent",
    "create_creative_agent",
    "create_deep_analysis_agent",
    "ANALYST_SUB_PERSONALITIES",
    "CODER_SUB_PERSONALITIES",
    
    # Dynamic prompts
    "DynamicPromptBuilder",
    "get_dynamic_prompt_builder",
]
