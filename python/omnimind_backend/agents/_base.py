"""Agent personality protocol and base agent definition.

Provides ``AgentPersonality`` (structural typing) and ``BaseAgent``
(immutable configuration) that every personality factory must produce.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)


@runtime_checkable
class AgentPersonality(Protocol):
    """Structural contract that every agent personality must satisfy."""

    @property
    def agent_type(self) -> AgentType: ...

    @property
    def system_prompt(self) -> str: ...

    @property
    def tools(self) -> list[ToolScope]: ...

    @property
    def thinking_level(self) -> ThinkingLevel: ...


@dataclass(frozen=True, slots=True)
class BaseAgent:
    """Immutable agent configuration produced by personality factories.

    A ``BaseAgent`` encapsulates everything the runtime needs to know
    about a particular personality: its prompt, tools, thinking depth,
    sandbox policy, etc.
    """

    agent_type: AgentType
    system_prompt: str
    tools: list[ToolScope] = field(default_factory=list)
    default_model: str | None = None
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    sandbox: SandboxMode = SandboxMode.NONE
    keep_context: bool = True
