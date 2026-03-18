"""Tests for workflow plans carrying explicit executable steps."""

from mindflow_backend.orchestrator.chain_integration import build_workflow_plan
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    Priority,
    ThinkingLevel,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType
from mindflow_backend.schemas.orchestration.workflow import WorkflowRouteDecision


def test_single_agent_plan_creates_one_step_with_specialist_identity() -> None:
    route = WorkflowRouteDecision(
        rationale="Security investigation",
        execution_strategy=ExecutionStrategy.SINGLE_AGENT,
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.SECURITY_GUARD,
        task="Audit auth flow",
        thinking=ThinkingLevel.HIGH,
        priority=Priority.HIGH,
    )

    plan = build_workflow_plan(message="audit", route=route)

    assert len(plan.steps) == 1
    assert plan.steps[0].agent_id == "analyst:security_guard"
    assert plan.steps[0].specialist == SpecialistType.SECURITY_GUARD


def test_coding_task_plan_keeps_specialist_identities_across_steps() -> None:
    route = WorkflowRouteDecision(
        rationale="Architecture-heavy implementation",
        execution_strategy=ExecutionStrategy.CHAIN,
        agent_role=AgentType.CODER,
        specialist=SpecialistType.ARCH_TECH,
        task="Implement payment architecture",
        thinking=ThinkingLevel.HIGH,
        priority=Priority.HIGH,
    )

    plan = build_workflow_plan(message="implement payment architecture", route=route)

    assert plan.chain_id == "coding_task"
    assert [step.agent_id for step in plan.steps] == [
        "analyst:deep_iteration",
        "coder:arch_tech",
        "analyst:critic",
    ]


def test_file_analysis_plan_preserves_selected_specialist() -> None:
    route = WorkflowRouteDecision(
        rationale="Workspace-wide deep analysis",
        execution_strategy=ExecutionStrategy.CHAIN,
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.DEEP_ITERATION,
        task="Map the codebase",
        thinking=ThinkingLevel.HIGH,
        priority=Priority.HIGH,
    )

    plan = build_workflow_plan(
        message="analise esta codebase",
        route=route,
        folder_path="/repo",
    )

    assert plan.chain_id == "file_analysis"
    assert len(plan.steps) == 1
    assert plan.steps[0].agent_id == "analyst:deep_iteration"
