"""ArchTech agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.arch_tech import ARCH_TECH_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import AgentType, ThinkingLevel, ToolScope


def create_arch_tech_agent() -> BaseAgent:
    """Create the ArchTech personality with filesystem and code analysis tools."""
    return BaseAgent(
        agent_type=AgentType.ARCH_TECH,
        system_prompt=ARCH_TECH_SYSTEM_PROMPT,
        tools=[ToolScope.FILESYSTEM, ToolScope.CODE_ANALYSIS],
        thinking_level=ThinkingLevel.HIGH,
        keep_context=True,
    )
