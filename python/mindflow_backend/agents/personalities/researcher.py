"""Researcher agent personality factory."""

from __future__ import annotations

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.prompts.researcher import RESEARCHER_SYSTEM_PROMPT
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ThinkingLevel, ToolScope


def create_researcher_agent() -> BaseAgent:
    """Create the Researcher personality with web search tools."""
    return BaseAgent(
        agent_type=AgentType.RESEARCHER,
        system_prompt=RESEARCHER_SYSTEM_PROMPT,
        tools=[ToolScope.WEB_SEARCH, ToolScope.BROWSER_SEARCH],
        thinking_level=ThinkingLevel.HIGH,
        keep_context=True,
    )
