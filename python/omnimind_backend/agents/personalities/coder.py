"""Coder agent personality factory.

Sub-personalities allow Coder to adopt specialized roles at runtime.
The DynamicSystemPrompt dispatcher will select appropriate sub-personality
based on delegation context.
"""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.coder import (
    CODER_SYSTEM_PROMPT,
    compose_coder_prompt,
)
from omnimind_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)

# ---------------------------------------------------------------------------
# Sub-personality registry
# Used by DynamicSystemPrompt dispatcher to swap prompts at delegation time.
# ---------------------------------------------------------------------------

CODER_SUB_PERSONALITIES: dict[str, str] = {
    "core": CODER_SYSTEM_PROMPT,
    "arch_tech": compose_coder_prompt("core", "arch_tech"),
}


def create_coder_agent() -> BaseAgent:
    """Create Coder personality with filesystem and shell tools."""
    return BaseAgent(
        agent_type=AgentType.CODER,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.FULL,
        keep_context=True,
    )
