"""Analyst agent personality factory.

Sub-personalities allow Analyst to adopt specialized roles at runtime.
The DynamicSystemPrompt dispatcher will select appropriate sub-personality
based on delegation context.
"""

from __future__ import annotations

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.prompts.analyst import (
    ANALYST_SYSTEM_PROMPT,
    compose_analyst_prompt,
)
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ThinkingLevel, ToolScope

# ---------------------------------------------------------------------------
# Sub-personality registry
# Used by DynamicSystemPrompt dispatcher to swap prompts at delegation time.
# ---------------------------------------------------------------------------

ANALYST_SUB_PERSONALITIES: dict[str, str] = {
    "core": ANALYST_SYSTEM_PROMPT,
    "security_guard": compose_analyst_prompt("core", "security_guard"),
    "critic": compose_analyst_prompt("core", "critic"),
    "brainstorm": compose_analyst_prompt("core", "brainstorm"),
    "planner": compose_analyst_prompt("core", "planner"),
}


def create_analyst_agent() -> BaseAgent:
    """Create Analyst personality — codebase context extractor with read-only access."""
    return BaseAgent(
        agent_type=AgentType.ANALYST,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        thinking_level=ThinkingLevel.MEDIUM,
        keep_context=True,
    )
