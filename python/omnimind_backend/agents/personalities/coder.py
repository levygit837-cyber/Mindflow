"""Coder agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.coder import CODER_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)


def create_coder_agent() -> BaseAgent:
    """Create the Coder personality with filesystem and shell tools."""
    return BaseAgent(
        agent_type=AgentType.CODER,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.FULL,
        keep_context=True,
    )
