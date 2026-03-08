"""Tests for the agent registry."""

import pytest

from mindflow_backend.agents._registry import (
    get_registry,
    register_all_specialists,
)
from mindflow_backend.agents.specialists.factories import create_coder_agent
from mindflow_backend.schemas.orchestrator import AgentType


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Reset the global registry before and after each test."""
    registry = get_registry()
    registry.clear()
    yield  # type: ignore[misc]
    registry.clear()


def test_register_and_get() -> None:
    registry = AgentRegistry()
    agent = create_coder_agent()
    registry.register(agent)
    assert registry.get(AgentType.CODER) is agent


def test_get_unregistered_raises() -> None:
    registry = AgentRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.get(AgentType.ANALYST)


def test_list_all() -> None:
    registry = AgentRegistry()
    agent = create_coder_agent()
    registry.register(agent)
    assert len(registry.list_all()) == 1
    assert registry.list_all()[0] is agent


def test_count() -> None:
    registry = AgentRegistry()
    assert registry.count == 0
    registry.register(create_coder_agent())
    assert registry.count == 1


def test_clear() -> None:
    registry = AgentRegistry()
    registry.register(create_coder_agent())
    registry.clear()
    assert registry.count == 0


def test_register_all_personalities() -> None:
    register_all_personalities()
    registry = get_registry()
    assert registry.count == 7
    # Verify all types are present
    for agent_type in AgentType:
        agent = registry.get(agent_type)
        assert agent.agent_type == agent_type
