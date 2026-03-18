"""Regression tests for agent registry lookups by stable agent_id."""

from __future__ import annotations

from mindflow_backend.agents._registry import get_agent, get_registry
from mindflow_backend.agents.specialists.factories import create_orchestrator_agent


def test_get_agent_accepts_agent_id_without_positional_agent_type() -> None:
    registry = get_registry()
    registry.clear()
    try:
        agent = create_orchestrator_agent()
        registry.register(agent)

        resolved = get_agent(agent_id="orchestrator")

        assert resolved is agent
    finally:
        registry.clear()
