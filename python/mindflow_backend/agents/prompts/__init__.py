"""System prompts for MindFlow agents.

Organized by function and category for clarity and maintainability.
Core personalities provide foundational behaviors, while specialized prompts
add context-specific capabilities. Composite prompts maintain backward compatibility.
"""

from __future__ import annotations

# Base utilities
from mindflow_backend.agents.prompts.base import MINDFLOW_PREAMBLE, build_system_prompt, build_assembled_prompt

# Assembler and layers (Phase 1: Prompt Injection System)
from mindflow_backend.agents.prompts.assembler import AssemblyContext, PromptAssembler
from mindflow_backend.agents.prompts.layers import (
    BasePromptLayer,
    EnvironmentLayer,
    GitContextLayer,
    MemoryFileLayer,
    ToolDescriptionLayer,
)

# Composite prompts (pre-built combinations for backward compatibility)
from mindflow_backend.agents.prompts.composite import (
    FULL_ANALYST_PROMPT,
    FULL_CODER_PROMPT,
    FULL_ORCHESTRATOR_PROMPT,
)

# Core personalities (primary agent identities)
from mindflow_backend.agents.prompts.core import (
    ANALYST_SYSTEM_PROMPT,
    CODER_SYSTEM_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
)

# Specialized functions (context-specific capabilities)
from mindflow_backend.agents.prompts.specialized import (
    AGENT_DELEGATION_PROMPT,
    ARCHITECTURE_REVIEW_PROMPT,
    BRAINSTORMING_PROMPT,
    CODE_REVIEW_PROMPT,
    CONTEXT_GOVERNANCE_PROMPT,
    DEEP_ANALYSIS_PROMPT,
    MEMORY_PROTOCOL_PROMPT,
    ORCHESTRATOR_PLANNING_PROMPT,
    ORCHESTRATOR_REFLECTION_PROMPT,
    PLANNING_PROMPT,
    SECURITY_ANALYSIS_PROMPT,
)

# Legacy exports (maintain backward compatibility)
ANALYST_SYSTEM_PROMPT_LEGACY = FULL_ANALYST_PROMPT
CODER_SYSTEM_PROMPT_LEGACY = FULL_CODER_PROMPT
ORCHESTRATOR_SYSTEM_PROMPT_LEGACY = FULL_ORCHESTRATOR_PROMPT

__all__ = [
    # Base utilities
    "build_system_prompt",
    "build_assembled_prompt",
    "MINDFLOW_PREAMBLE",
    # Assembler and layers
    "AssemblyContext",
    "PromptAssembler",
    "BasePromptLayer",
    "EnvironmentLayer",
    "GitContextLayer",
    "MemoryFileLayer",
    "ToolDescriptionLayer",
    # Core personalities
    "ANALYST_SYSTEM_PROMPT",
    "CODER_SYSTEM_PROMPT",
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "RESEARCHER_SYSTEM_PROMPT",
    # Specialized functions
    "SECURITY_ANALYSIS_PROMPT",
    "ARCHITECTURE_REVIEW_PROMPT",
    "CODE_REVIEW_PROMPT",
    "BRAINSTORMING_PROMPT",
    "DEEP_ANALYSIS_PROMPT",
    "CONTEXT_GOVERNANCE_PROMPT",
    "AGENT_DELEGATION_PROMPT",
    "MEMORY_PROTOCOL_PROMPT",
    "ORCHESTRATOR_REFLECTION_PROMPT",
    "ORCHESTRATOR_PLANNING_PROMPT",
    "PLANNING_PROMPT",
    # Composite prompts
    "FULL_ANALYST_PROMPT",
    "FULL_CODER_PROMPT",
    "FULL_ORCHESTRATOR_PROMPT",
    # Legacy exports
    "ANALYST_SYSTEM_PROMPT_LEGACY",
    "CODER_SYSTEM_PROMPT_LEGACY",
    "ORCHESTRATOR_SYSTEM_PROMPT_LEGACY",
]