"""Researcher agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.researcher import RESEARCHER_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import AgentType, ThinkingLevel, ToolScope


def create_researcher_agent() -> BaseAgent:
    """Create the Researcher personality with web search tools."""
    return BaseAgent(
        agent_type=AgentType.RESEARCHER,
        system_prompt=RESEARCHER_SYSTEM_PROMPT,
        tools=[ToolScope.WEB_SEARCH],
        thinking_level=ThinkingLevel.MEDIUM,
        keep_context=True,
    )
