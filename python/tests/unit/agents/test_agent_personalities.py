"""Tests for agent personality factories."""

from omnimind_backend.agents._base import AgentPersonality, BaseAgent
from omnimind_backend.agents.personalities import (
    create_analyst_agent,
    create_arch_tech_agent,
    create_coder_agent,
    create_critic_agent,
    create_researcher_agent,
)
from omnimind_backend.agents.personalities.creative import create_creative_agent
from omnimind_backend.agents.personalities.security_guard import create_security_guard_agent
from omnimind_backend.schemas.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)


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
    assert agent.thinking_level == ThinkingLevel.MEDIUM
    assert "Researcher" in agent.system_prompt


def test_arch_tech_agent_creation() -> None:
    agent = create_arch_tech_agent()
    assert agent.agent_type == AgentType.ARCH_TECH
    assert ToolScope.FILESYSTEM in agent.tools
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert "ArchTech" in agent.system_prompt


def test_critic_agent_creation() -> None:
    agent = create_critic_agent()
    assert agent.agent_type == AgentType.CRITIC
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert agent.thinking_level == ThinkingLevel.MEDIUM
    assert "Critic" in agent.system_prompt


def test_creative_agent_creation() -> None:
    agent = create_creative_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_type == AgentType.CREATIVE
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert ToolScope.FILESYSTEM in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert "Creative" in agent.system_prompt
    assert "diverge" in agent.system_prompt.lower() or "converge" in agent.system_prompt.lower()


def test_security_guard_agent_creation() -> None:
    agent = create_security_guard_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_type == AgentType.SECURITY_GUARD
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
        create_arch_tech_agent,
        create_critic_agent,
        create_creative_agent,
        create_security_guard_agent,
    ):
        agent = factory()
        assert isinstance(agent, AgentPersonality)


def test_base_agent_is_frozen() -> None:
    agent = create_coder_agent()
    import pytest

    with pytest.raises(AttributeError):
        agent.agent_type = AgentType.ANALYST  # type: ignore[misc]
