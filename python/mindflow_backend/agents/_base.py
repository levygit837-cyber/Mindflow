"""Agent specialist protocol and base agent definition.

Provides ``AgentPersonality`` (structural typing) and ``BaseAgent``
(immutable configuration) that every specialist factory must produce.

The canonical role/specialization vocabulary lives in orchestration schemas.
This module only defines the runtime container for those contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType


@runtime_checkable
class AgentPersonality(Protocol):
    """Structural contract that every agent specialist must satisfy."""

    @property
    def agent_role(self) -> AgentType: ...

    @property
    def agent_type(self) -> AgentType: ...

    @property
    def specialist(self) -> SpecialistType | None: ...

    @property
    def system_prompt(self) -> str: ...

    @property
    def tools(self) -> list[ToolScope]: ...

    @property
    def thinking_level(self) -> ThinkingLevel: ...


@dataclass(slots=True)
class BaseAgent:
    """Immutable agent configuration produced by specialist factories.

    A ``BaseAgent`` encapsulates everything the runtime needs to know
    about a particular specialist: its prompt, tools, thinking depth,
    sandbox policy, etc.
    """

    agent_role: AgentType
    system_prompt: str
    specialist: SpecialistType | None = None
    custom_agent_id: str | None = None
    tools: list[ToolScope] = field(default_factory=list)
    default_model: str | None = None
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    sandbox: SandboxMode = SandboxMode.NONE
    keep_context: bool = True
    # Root working directory for filesystem operations.
    # When set, tools use this as the base path for relative paths and the
    # agent's system prompt is augmented with a "your working directory is …"
    # instruction so the LLM knows where to work.
    root_dir: str | None = None
    # Communication mixin — injected by DelegationEngine when bus is available.
    # Type: AgentCommunicationMixin | None (avoiding circular import)
    comm: Any = None

    @property
    def agent_type(self) -> AgentType:
        """Compatibility alias for older callers that still expect ``agent_type``."""
        return self.agent_role

    @property
    def agent_id(self) -> str:
        """Stable registry identity used for role + specialization lookups."""
        if self.custom_agent_id:
            return self.custom_agent_id
        if self.specialist is None:
            return self.agent_role.value
        return f"{self.agent_role.value}:{self.specialist.value}"

    @property
    def has_p2p(self) -> bool:
        """True se o agente tem capacidade de comunicação P2P ativa."""
        return self.comm is not None and self.comm._bus.is_available
