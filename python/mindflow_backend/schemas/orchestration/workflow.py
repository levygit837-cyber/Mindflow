"""Workflow contracts for router -> planner -> executor orchestration.

The router decides strategy and target identity only. The planner resolves the
final execution plan consumed by the canonical simple-flow runtime.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ChainType,
    ExecutionStrategy,
    GraphType,
    OrchestratorDecision,
    Priority,
    ThinkingLevel,
    ToolScope,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType


class WorkflowRouteDecision(BaseModel):
    """Final router output before planning-specific expansion."""

    rationale: str = ""
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SINGLE_AGENT
    agent_role: AgentType = AgentType.CODER
    specialist: SpecialistType | None = None
    task: str = ""
    thinking: ThinkingLevel = ThinkingLevel.MEDIUM
    priority: Priority = Priority.NORMAL
    tools: list[ToolScope] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @property
    def agent_id(self) -> str:
        if self.specialist is None:
            return self.agent_role.value
        return f"{self.agent_role.value}:{self.specialist.value}"


class WorkflowStep(BaseModel):
    """Executable step produced by the planner."""

    step_id: str
    agent_id: str
    agent_role: AgentType
    specialist: SpecialistType | None = None
    objective: str = ""
    tools: list[ToolScope] = Field(default_factory=list)
    sandbox: str = ""
    thinking: ThinkingLevel = ThinkingLevel.MEDIUM
    context_strategy: str = "maintain"
    depends_on: list[str] = Field(default_factory=list)


class WorkflowPlan(BaseModel):
    """Planner output consumed by the executor without further routing logic."""

    route: WorkflowRouteDecision
    tools: list[ToolScope] = Field(default_factory=list)
    steps: list[WorkflowStep] = Field(default_factory=list)
    chain_id: str | None = None
    chain_type: ChainType | None = None
    graph_id: str | None = None
    graph_type: GraphType | None = None
    planner_rule: str | None = None

    def to_decision(self) -> OrchestratorDecision:
        """Convert workflow plan into the executor-facing decision payload."""
        return OrchestratorDecision(
            rationale=self.route.rationale,
            agent=self.route.agent_role,
            agent_role=self.route.agent_role,
            specialist=self.route.specialist,
            agent_id=self.route.agent_id,
            task=self.route.task,
            thinking=self.route.thinking,
            priority=self.route.priority,
            tools=list(self.tools or self.route.tools),
            execution_strategy=self.route.execution_strategy,
            chain_id=self.chain_id,
            chain_type=self.chain_type,
            graph_id=self.graph_id,
            graph_type=self.graph_type,
        )
