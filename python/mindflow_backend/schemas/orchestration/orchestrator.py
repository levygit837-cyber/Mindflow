"""Orchestrator data contracts — enums, models, and decision schema.

Defines the vocabulary for the orchestrator routing layer: agent types,
thinking levels, tool scopes, and the ``OrchestratorDecision`` payload
that drives agent selection and execution configuration.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

# Keep orchestration schemas lightweight: do not import graphs/runtime modules here.
from mindflow_backend.schemas.orchestration.specialists import SpecialistType

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


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


class ThinkingMode(StrEnum):
    """Strategy for reasoning execution."""

    NORMAL = "normal"
    DECOMPOSITION = "decomposition"


class ToolScope(StrEnum):
    """Capability scopes available to agents."""

    FILESYSTEM = "filesystem"
    SHELL = "shell"
    WEB_SEARCH = "web_search"
    BROWSER_SEARCH = "browser_search"
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


class ExecutionStrategy(StrEnum):
    """How the orchestrator intends to execute a request."""

    DIRECT_RESPONSE = "direct_response"  # Orchestrator responds directly without delegating
    SINGLE_AGENT = "single_agent"
    CHAIN = "chain"
    GRAPH = "graph"


class ChainType(StrEnum):
    """High-level chain categories (used for routing/analytics)."""

    CODING_TASK = "coding_task"
    ANALYSIS_TASK = "analysis_task"
    FILE_ANALYSIS = "file_analysis"
    RESEARCH = "research"
    REVIEW_ONLY = "review_only"


class GraphType(StrEnum):
    """Graph categories (kept here to avoid importing graph modules in schemas)."""

    SIMPLE = "simple"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    CYCLIC = "cyclic"
    DECOMPOSITION = "decomposition"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChainStep(BaseModel):
    """A single step in a multi-agent chain."""

    agent: AgentType
    specialist: SpecialistType | None = None
    task: str
    tools: list[ToolScope] = Field(default_factory=list)


class OrchestratorDecision(BaseModel):
    """Complete routing decision produced by the orchestrator.

    Encapsulates *every* parameter needed to configure and execute an
    agent for a given user request.
    """

    rationale: str = ""
    agent: AgentType = AgentType.CODER
    agent_role: AgentType | None = None
    specialist: SpecialistType | None = None
    agent_id: str | None = None
    task: str = ""
    model: str | None = None
    thinking: ThinkingLevel = ThinkingLevel.MEDIUM
    thinking_mode: ThinkingMode = ThinkingMode.NORMAL
    tools: list[ToolScope] = Field(default_factory=list)
    priority: Priority = Priority.NORMAL
    keep_context: bool = True
    sandbox: SandboxMode = SandboxMode.NONE
    chain: list[ChainStep] = Field(default_factory=list)
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SINGLE_AGENT
    chain_id: str | None = None
    chain_type: ChainType | None = None
    graph_id: str | None = None
    graph_type: GraphType | None = None
    complexity_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _normalize_identity(self) -> "OrchestratorDecision":
        """Keep legacy ``agent`` and canonical ``agent_role`` aligned."""
        if self.agent_role is None:
            self.agent_role = self.agent
        self.agent = self.agent_role
        if self.agent_id is None:
            if self.specialist is None:
                self.agent_id = self.agent_role.value
            else:
                self.agent_id = f"{self.agent_role.value}:{self.specialist.value}"
        return self
