"""Tests for canonical orchestrator decision schemas."""

import pytest
from pydantic import ValidationError

from mindflow_backend.schemas.orchestrator import (
    AgentType,
    ChainStep,
    OrchestratorDecision,
    Priority,
    SandboxMode,
    SpecialistType,
    ThinkingLevel,
    ThinkingMode,
    ToolScope,
)


def test_agent_type_values_are_base_roles() -> None:
    assert AgentType.CODER == "coder"
    assert AgentType.ANALYST == "analyst"
    assert AgentType.RESEARCHER == "researcher"
    assert AgentType.ORCHESTRATOR == "orchestrator"
    assert len(AgentType) == 4


def test_tool_scope_values_include_browser_search() -> None:
    # Verify the core scopes are present; new scopes may be added over time.
    required = {
        "filesystem",
        "shell",
        "web_search",
        "browser_search",
        "code_analysis",
        "database",
        "memory",
        "planning",
        "delegation",
        "pinchtab_fleet",
        "pinchtab_browser",
    }
    assert required.issubset({s.value for s in ToolScope})


def test_orchestrator_decision_defaults() -> None:
    decision = OrchestratorDecision()
    assert decision.agent == AgentType.CODER
    assert decision.agent_role == AgentType.CODER
    assert decision.specialist is None
    assert decision.agent_id == "coder"
    assert decision.thinking == ThinkingLevel.MEDIUM
    assert decision.thinking_mode == ThinkingMode.NORMAL
    assert decision.priority == Priority.NORMAL
    assert decision.sandbox == SandboxMode.NONE
    assert decision.keep_context is True
    assert decision.complexity_score == 0.0
    assert decision.tools == []
    assert decision.chain == []
    assert decision.model is None


def test_orchestrator_decision_supports_role_and_specialization() -> None:
    decision = OrchestratorDecision(
        rationale="Security review is required",
        agent=AgentType.ANALYST,
        specialist=SpecialistType.SECURITY_GUARD,
        task="Audit the auth flow",
        thinking=ThinkingLevel.HIGH,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        priority=Priority.HIGH,
        sandbox=SandboxMode.READ_ONLY,
        complexity_score=0.8,
    )
    assert decision.agent == AgentType.ANALYST
    assert decision.agent_role == AgentType.ANALYST
    assert decision.specialist == SpecialistType.SECURITY_GUARD
    assert decision.agent_id == "analyst:security_guard"
    assert decision.thinking == ThinkingLevel.HIGH
    assert ToolScope.CODE_ANALYSIS in decision.tools
    assert decision.complexity_score == 0.8


def test_orchestrator_decision_serialization_round_trips_specialist_identity() -> None:
    decision = OrchestratorDecision(
        agent=AgentType.CODER,
        specialist=SpecialistType.ARCH_TECH,
        task="Design a caching subsystem",
        tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
    )
    data = decision.model_dump()
    assert data["agent"] == "coder"
    assert data["agent_role"] == "coder"
    assert data["specialist"] == "arch_tech"
    assert data["agent_id"] == "coder:arch_tech"

    restored = OrchestratorDecision.model_validate(data)
    assert restored == decision


def test_chain_step_supports_specialist_identity() -> None:
    step = ChainStep(
        agent=AgentType.ANALYST,
        specialist=SpecialistType.CRITIC,
        task="Review the implementation",
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
    )
    assert step.agent == AgentType.ANALYST
    assert step.specialist == SpecialistType.CRITIC
    assert len(step.tools) == 2


def test_complexity_score_bounds() -> None:
    with pytest.raises(ValidationError):
        OrchestratorDecision(complexity_score=1.5)

    with pytest.raises(ValidationError):
        OrchestratorDecision(complexity_score=-0.1)

    OrchestratorDecision(complexity_score=0.0)
    OrchestratorDecision(complexity_score=1.0)
