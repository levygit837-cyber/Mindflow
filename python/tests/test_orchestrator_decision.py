"""Tests for orchestrator decision schemas."""

from omnimind_backend.schemas.orchestrator import (
    AgentType,
    ChainStep,
    OrchestratorDecision,
    Priority,
    SandboxMode,
    ThinkingLevel,
    ThinkingMode,
    ToolScope,
)

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


def test_agent_type_values() -> None:
    assert AgentType.CODER == "coder"
    assert AgentType.ANALYST == "analyst"
    assert AgentType.RESEARCHER == "researcher"
    assert AgentType.ARCH_TECH == "arch_tech"
    assert AgentType.CRITIC == "critic"
    assert len(AgentType) == 7


def test_thinking_level_values() -> None:
    assert set(ThinkingLevel) == {"NONE", "LOW", "MEDIUM", "HIGH"}


def test_tool_scope_values() -> None:
    expected = {"filesystem", "shell", "web_search", "code_analysis", "database"}
    assert set(ToolScope) == expected


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_orchestrator_decision_defaults() -> None:
    decision = OrchestratorDecision()
    assert decision.agent == AgentType.CODER
    assert decision.thinking == ThinkingLevel.MEDIUM
    assert decision.thinking_mode == ThinkingMode.NORMAL
    assert decision.priority == Priority.NORMAL
    assert decision.sandbox == SandboxMode.NONE
    assert decision.keep_context is True
    assert decision.complexity_score == 0.0
    assert decision.tools == []
    assert decision.chain == []
    assert decision.model is None


def test_orchestrator_decision_custom_values() -> None:
    decision = OrchestratorDecision(
        rationale="User asked to analyze code",
        agent=AgentType.ANALYST,
        task="Analyze the codebase for complexity metrics",
        thinking=ThinkingLevel.HIGH,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        priority=Priority.HIGH,
        sandbox=SandboxMode.READ_ONLY,
        complexity_score=0.8,
    )
    assert decision.agent == AgentType.ANALYST
    assert decision.thinking == ThinkingLevel.HIGH
    assert ToolScope.CODE_ANALYSIS in decision.tools
    assert decision.complexity_score == 0.8


def test_orchestrator_decision_serialization() -> None:
    decision = OrchestratorDecision(
        agent=AgentType.RESEARCHER,
        task="Find latest FastAPI docs",
        tools=[ToolScope.WEB_SEARCH],
    )
    data = decision.model_dump()
    assert data["agent"] == "researcher"
    assert data["tools"] == ["web_search"]

    # Round-trip
    restored = OrchestratorDecision.model_validate(data)
    assert restored == decision


def test_chain_step_creation() -> None:
    step = ChainStep(
        agent=AgentType.CODER,
        task="Implement the solution",
        tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
    )
    assert step.agent == AgentType.CODER
    assert len(step.tools) == 2


def test_orchestrator_decision_with_chain() -> None:
    decision = OrchestratorDecision(
        agent=AgentType.ARCH_TECH,
        task="Design and implement a caching layer",
        chain=[
            ChainStep(agent=AgentType.ARCH_TECH, task="Design the architecture"),
            ChainStep(
                agent=AgentType.CODER,
                task="Implement the design",
                tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
            ),
            ChainStep(agent=AgentType.CRITIC, task="Review the implementation"),
        ],
    )
    assert len(decision.chain) == 3
    assert decision.chain[0].agent == AgentType.ARCH_TECH
    assert decision.chain[1].agent == AgentType.CODER
    assert decision.chain[2].agent == AgentType.CRITIC


def test_complexity_score_bounds() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        OrchestratorDecision(complexity_score=1.5)

    with pytest.raises(ValidationError):
        OrchestratorDecision(complexity_score=-0.1)

    # Boundary values should be valid
    OrchestratorDecision(complexity_score=0.0)
    OrchestratorDecision(complexity_score=1.0)
