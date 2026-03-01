"""Orchestrator data contracts — enums, models, and decision schema.

Defines the vocabulary for the orchestrator routing layer: agent types,
thinking levels, tool scopes, and the ``OrchestratorDecision`` payload
that drives agent selection and execution configuration.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentType(StrEnum):
    """Available agent personalities."""

    CODER = "coder"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    ARCH_TECH = "arch_tech"
    CRITIC = "critic"


class ThinkingLevel(StrEnum):
    """Depth of reasoning the agent should apply."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ThinkingMode(StrEnum):
    """Strategy for reasoning execution."""

    NORMAL = "normal"
    DECOMPOSITION = "decomposition"


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


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChainStep(BaseModel):
    """A single step in a multi-agent chain."""

    agent: AgentType
    task: str
    tools: list[ToolScope] = Field(default_factory=list)


class OrchestratorDecision(BaseModel):
    """Complete routing decision produced by the orchestrator.

    Encapsulates *every* parameter needed to configure and execute an
    agent for a given user request.
    """

    rationale: str = ""
    agent: AgentType = AgentType.CODER
    task: str = ""
    model: str | None = None
    thinking: ThinkingLevel = ThinkingLevel.MEDIUM
    thinking_mode: ThinkingMode = ThinkingMode.NORMAL
    tools: list[ToolScope] = Field(default_factory=list)
    priority: Priority = Priority.NORMAL
    keep_context: bool = True
    sandbox: SandboxMode = SandboxMode.NONE
    chain: list[ChainStep] = Field(default_factory=list)
    complexity_score: float = Field(default=0.0, ge=0.0, le=1.0)
