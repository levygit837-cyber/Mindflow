"""Orchestrator agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)


def create_orchestrator_agent() -> BaseAgent:
    """Create Orchestrator personality with no direct tools."""
    return BaseAgent(
        agent_type=AgentType.ORCHESTRATOR,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=[],  # Orchestrator delegates, doesn't use tools directly
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.NONE,  # No direct system access
        keep_context=True,
    )
