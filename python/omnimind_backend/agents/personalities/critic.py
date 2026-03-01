"""Critic agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.critic import CRITIC_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import AgentType, ThinkingLevel, ToolScope


def create_critic_agent() -> BaseAgent:
    """Create the Critic personality with code analysis tools."""
    return BaseAgent(
        agent_type=AgentType.CRITIC,
        system_prompt=CRITIC_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS],
        thinking_level=ThinkingLevel.MEDIUM,
        keep_context=True,
    )
