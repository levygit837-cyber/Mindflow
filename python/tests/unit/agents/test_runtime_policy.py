"""Tests for canonical runtime policy and specialist registration."""

from mindflow_backend.agents._registry import get_registry, register_all_specialists
from mindflow_backend.agents.prompts.specialized.deep_analysis import DEEP_ANALYSIS_PROMPT
from mindflow_backend.agents.specialists.factories import (
    create_analyst_agent,
    create_coder_agent,
    create_deep_analysis_agent,
    create_orchestrator_agent,
    create_researcher_agent,
)
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.base.tool_detection import get_tool_execution_strategy
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.schemas.orchestration.specialists import SpecialistType


def test_deep_iteration_uses_only_deep_prompt() -> None:
    agent = create_deep_analysis_agent()
    assert agent.system_prompt.startswith(DEEP_ANALYSIS_PROMPT)


def test_orchestrator_runtime_policy_exposes_memory_and_planning_tools() -> None:
    agent = create_orchestrator_agent()
    sandbox = MindFlowSandbox(root_dir="/tmp/project", read_only=False)
    registry = create_default_registry(sandbox, session_id="test-session")

    tools = registry.get_tools_for_agent(agent)
    tool_names = {tool.name for tool in tools}

    assert "write_todos" in tool_names
    assert "recall_session_memory" in tool_names


def test_production_runtime_policies_are_callable_only() -> None:
    sandbox = MindFlowSandbox(root_dir="/tmp/project", read_only=False)
    registry = create_default_registry(sandbox, session_id="test-session")

    for agent in (
        create_orchestrator_agent(),
        create_analyst_agent(),
        create_coder_agent(),
        create_researcher_agent(),
    ):
        tools = registry.get_tools_for_agent(agent)
        assert tools
        assert get_tool_execution_strategy(tools) == "callable"


def test_register_all_specialists_no_longer_registers_creative() -> None:
    registry = get_registry()
    registry.clear()

    register_all_specialists()

    all_agents = registry.list_all()
    creative_specialist = getattr(SpecialistType, "CREATIVE", None)
    assert all(
        creative_specialist is None or agent.specialist != creative_specialist
        for agent in all_agents
    )
    assert not any(agent.agent_id == "creative" or agent.agent_id.endswith(":creative") for agent in all_agents)

    registry.clear()
