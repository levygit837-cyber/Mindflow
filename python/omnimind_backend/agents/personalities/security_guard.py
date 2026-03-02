"""SecurityGuard agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.security_guard import SECURITY_GUARD_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)


def create_security_guard_agent() -> BaseAgent:
    """Create the SecurityGuard personality with security analysis tools."""
    return BaseAgent(
        agent_type=AgentType.SECURITY_GUARD,
        system_prompt=SECURITY_GUARD_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )
