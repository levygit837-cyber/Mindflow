"""Tests for agent specialist factories."""

from mindflow_backend.agents._base import AgentPersonality, BaseAgent
from mindflow_backend.agents.specialists import (
    create_analyst_agent,
    create_architecture_agent,
    create_brainstorm_agent,
    create_coder_agent,
    create_deep_analysis_agent,
    create_researcher_agent,
    create_review_agent,
    create_security_agent,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType
from mindflow_backend.schemas.orchestrator import AgentType, SandboxMode, ThinkingLevel, ToolScope


def test_coder_agent_creation() -> None:
    agent = create_coder_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_type == AgentType.CODER
    assert ToolScope.FILESYSTEM in agent.tools
    assert ToolScope.SHELL in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert agent.sandbox == SandboxMode.FULL
    assert agent.keep_context is True
    assert "Coder" in agent.system_prompt


def test_analyst_agent_creation() -> None:
    agent = create_analyst_agent()
    assert agent.agent_type == AgentType.ANALYST
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert ToolScope.FILESYSTEM in agent.tools
    assert agent.thinking_level == ThinkingLevel.MEDIUM
    assert "Analyst" in agent.system_prompt


def test_researcher_agent_creation() -> None:
    agent = create_researcher_agent()
    assert agent.agent_type == AgentType.RESEARCHER
    assert ToolScope.WEB_SEARCH in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert "Researcher" in agent.system_prompt


def test_arch_tech_agent_creation() -> None:
    agent = create_architecture_agent()
    assert agent.agent_role == AgentType.CODER
    assert agent.specialist == SpecialistType.ARCH_TECH
    assert ToolScope.FILESYSTEM in agent.tools
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert agent.sandbox == SandboxMode.FULL


def test_critic_agent_creation() -> None:
    agent = create_review_agent()
    assert agent.agent_role == AgentType.ANALYST
    assert agent.specialist == SpecialistType.CRITIC
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert agent.thinking_level == ThinkingLevel.MEDIUM
    assert "Critic" in agent.system_prompt


def test_brainstorm_agent_creation() -> None:
    agent = create_brainstorm_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_role == AgentType.ANALYST
    assert agent.specialist == SpecialistType.BRAINSTORM
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert ToolScope.FILESYSTEM in agent.tools
    assert agent.thinking_level == ThinkingLevel.MEDIUM
    assert "brainstorm" in agent.system_prompt.lower() or "alternative" in agent.system_prompt.lower()


def test_deep_iteration_agent_creation() -> None:
    agent = create_deep_analysis_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_role == AgentType.ANALYST
    assert agent.specialist == SpecialistType.DEEP_ITERATION
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert ToolScope.SHELL in agent.tools
    assert agent.sandbox == SandboxMode.READ_ONLY
    assert agent.thinking_level == ThinkingLevel.HIGH


def test_security_guard_agent_creation() -> None:
    agent = create_security_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_role == AgentType.ANALYST
    assert agent.specialist == SpecialistType.SECURITY_GUARD
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert ToolScope.FILESYSTEM in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert agent.sandbox == SandboxMode.READ_ONLY
    assert "SecurityGuard" in agent.system_prompt or "Security" in agent.system_prompt


def test_all_agents_satisfy_protocol() -> None:
    """Every factory must produce an object that satisfies AgentPersonality."""
    for factory in (
        create_coder_agent,
        create_analyst_agent,
        create_researcher_agent,
        create_review_agent,
        create_architecture_agent,
        create_brainstorm_agent,
        create_deep_analysis_agent,
        create_security_agent,
    ):
        agent = factory()
        assert isinstance(agent, AgentPersonality)


def test_base_agent_is_frozen() -> None:
    agent = create_coder_agent()
    import pytest

    with pytest.raises((AttributeError, TypeError)):
        agent.agent_type = AgentType.ANALYST  # type: ignore[misc]
