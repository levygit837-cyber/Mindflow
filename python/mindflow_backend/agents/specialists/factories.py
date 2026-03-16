"""Specialist agent factories.

Migrated from personalities/ system to maintain compatibility
while using the new specialist architecture.
"""

from __future__ import annotations

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.prompts.core.analyst import (
    ANALYST_SYSTEM_PROMPT,
    compose_analyst_prompt,
)
from mindflow_backend.agents.prompts.core.coder import (
    CODER_SYSTEM_PROMPT,
    compose_coder_prompt,
)
from mindflow_backend.agents.prompts.core.researcher import RESEARCHER_SYSTEM_PROMPT
from mindflow_backend.agents.prompts.core.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)
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
    return BaseAgent(
        agent_role=AgentType.ANALYST,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.MEDIUM,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )


def create_coder_agent() -> BaseAgent:
    """Create Coder specialist with filesystem and shell tools."""
    return BaseAgent(
        agent_role=AgentType.CODER,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.FULL,
        keep_context=True,
    )


def create_researcher_agent() -> BaseAgent:
    """Create the Researcher specialist with web search tools."""
    return BaseAgent(
        agent_role=AgentType.RESEARCHER,
        system_prompt=RESEARCHER_SYSTEM_PROMPT,
        tools=[ToolScope.WEB_SEARCH, ToolScope.BROWSER_SEARCH],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )


def create_orchestrator_agent() -> BaseAgent:
    """Create Orchestrator specialist with no direct tools."""
    return BaseAgent(
        agent_role=AgentType.ORCHESTRATOR,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=[],  # Orchestrator delegates, doesn't use tools directly
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.NONE,  # No direct system access
        keep_context=True,
    )


# Additional specialist factories for the new system
def create_security_agent() -> BaseAgent:
    """Create Security specialist for security-focused analysis."""
    return BaseAgent(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.SECURITY_GUARD,
        system_prompt=compose_analyst_prompt("core", "security_guard"),
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )


def create_review_agent() -> BaseAgent:
    """Create Review specialist for code review and criticism."""
    return BaseAgent(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.CRITIC,
        system_prompt=compose_analyst_prompt("core", "critic"),
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.MEDIUM,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )


def create_architecture_agent() -> BaseAgent:
    """Create Architecture specialist for architectural analysis."""
    return BaseAgent(
        agent_role=AgentType.CODER,
        specialist=SpecialistType.ARCH_TECH,
        system_prompt=compose_coder_prompt("core", "arch_tech"),
        tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.FULL,
        keep_context=True,
    )


def create_creative_agent() -> BaseAgent:
    """Create Creative specialist for brainstorming and ideation."""
    return BaseAgent(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.BRAINSTORM,
        system_prompt=compose_analyst_prompt("core", "brainstorm"),
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.MEDIUM,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )


def create_deep_analysis_agent() -> BaseAgent:
    """Create Deep Analysis specialist for thorough analysis."""
    return BaseAgent(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.DEEP_ITERATION,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )
