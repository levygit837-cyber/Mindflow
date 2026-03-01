"""Analyst agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.analyst import ANALYST_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import AgentType, ThinkingLevel, ToolScope


def create_analyst_agent() -> BaseAgent:
    """Create the Analyst personality with code analysis and filesystem tools."""
    return BaseAgent(
        agent_type=AgentType.ANALYST,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        thinking_level=ThinkingLevel.MEDIUM,
        keep_context=True,
    )
