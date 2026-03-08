"""Agent specialist protocol and base agent definition.

Provides ``AgentPersonality`` (structural typing) and ``BaseAgent``
(immutable configuration) that every specialist factory must produce.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from enum import StrEnum


class AgentType(StrEnum):
    """Available agent personalities."""

    CODER = "coder"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    ORCHESTRATOR = "orchestrator"


class ThinkingLevel(StrEnum):
    """Depth of reasoning the agent should apply."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ToolScope(StrEnum):
    """Capability scopes available to agents."""

    FILESYSTEM = "filesystem"
    SHELL = "shell"
    WEB_SEARCH = "web_search"
    CODE_ANALYSIS = "code_analysis"
    DATABASE = "database"


class SandboxMode(StrEnum):
    """Level of sandbox isolation for tool execution."""

    NONE = "none"
    READ_ONLY = "read_only"
    FULL = "full"


class Priority(StrEnum):
    """Execution priority for the orchestrator."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@runtime_checkable
class AgentPersonality(Protocol):
    """Structural contract that every agent specialist must satisfy."""

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
    """Immutable agent configuration produced by specialist factories.

    A ``BaseAgent`` encapsulates everything the runtime needs to know
    about a particular specialist: its prompt, tools, thinking depth,
    sandbox policy, etc.
    """

    agent_type: AgentType
    system_prompt: str
    tools: list[ToolScope] = field(default_factory=list)
    default_model: str | None = None
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    sandbox: SandboxMode = SandboxMode.NONE
    keep_context: bool = True
