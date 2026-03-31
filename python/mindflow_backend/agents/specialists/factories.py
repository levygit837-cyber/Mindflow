"""Specialist agent factories backed by the canonical runtime policy."""

from __future__ import annotations

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.prompts.core.analyst import (
    ANALYST_SYSTEM_PROMPT,
    compose_analyst_prompt,
)
from mindflow_backend.agents.prompts.core.coder import CODER_SYSTEM_PROMPT, compose_coder_prompt
from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from mindflow_backend.schemas.orchestration.specialists import SpecialistType

# ---------------------------------------------------------------------------
# Specialist variant registries
# Used by DynamicSystemPrompt dispatcher to swap prompts at delegation time.
# ---------------------------------------------------------------------------

ANALYST_SUB_PERSONALITIES: dict[str, str] = {
    "core": ANALYST_SYSTEM_PROMPT,
    "security_guard": compose_analyst_prompt("core", "security_guard"),
    "critic": compose_analyst_prompt("core", "critic"),
    "brainstorm": compose_analyst_prompt("core", "brainstorm"),
    "planner": compose_analyst_prompt("core", "planner"),
}

CODER_SUB_PERSONALITIES: dict[str, str] = {
    "core": CODER_SYSTEM_PROMPT,
    "arch_tech": compose_coder_prompt("core", "arch_tech"),
}


def create_analyst_agent() -> BaseAgent:
    """Create Analyst specialist — codebase context extractor with read-only access."""
    return get_agent_runtime_policy(AgentType.ANALYST).build_agent()


def create_coder_agent() -> BaseAgent:
    """Create Coder specialist with filesystem and shell tools."""
    return get_agent_runtime_policy(AgentType.CODER).build_agent()


def create_researcher_agent() -> BaseAgent:
    """Create the Researcher specialist with web search tools."""
    return get_agent_runtime_policy(AgentType.RESEARCHER).build_agent()


def create_orchestrator_agent() -> BaseAgent:
    """Create Orchestrator specialist with memory/planning-only tools."""
    return get_agent_runtime_policy(AgentType.ORCHESTRATOR).build_agent()


# Additional specialist factories for the new system
def create_security_agent() -> BaseAgent:
    """Create Security specialist for security-focused analysis."""
    return get_agent_runtime_policy(AgentType.ANALYST, specialist=SpecialistType.SECURITY_GUARD).build_agent()


def create_review_agent() -> BaseAgent:
    """Create Review specialist for code review and criticism."""
    return get_agent_runtime_policy(AgentType.ANALYST, specialist=SpecialistType.CRITIC).build_agent()


def create_architecture_agent() -> BaseAgent:
    """Create Architecture specialist for architectural analysis."""
    return get_agent_runtime_policy(AgentType.CODER, specialist=SpecialistType.ARCH_TECH).build_agent()


def create_brainstorm_agent() -> BaseAgent:
    """Create Brainstorm specialist for structured idea generation and exploration."""
    return get_agent_runtime_policy(AgentType.ANALYST, specialist=SpecialistType.BRAINSTORM).build_agent()


def create_deep_analysis_agent() -> BaseAgent:
    """Create Deep Analysis specialist for thorough analysis."""
    return get_agent_runtime_policy(AgentType.ANALYST, specialist=SpecialistType.DEEP_ITERATION).build_agent()
