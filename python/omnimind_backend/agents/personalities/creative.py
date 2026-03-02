"""Creative agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.creative import CREATIVE_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import (
    AgentType,
    ThinkingLevel,
    ToolScope,
)


def create_creative_agent() -> BaseAgent:
    """Create the Creative personality with divergent/convergent workflow."""
    return BaseAgent(
        agent_type=AgentType.CREATIVE,
        system_prompt=CREATIVE_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        thinking_level=ThinkingLevel.HIGH,
        keep_context=True,
    )
