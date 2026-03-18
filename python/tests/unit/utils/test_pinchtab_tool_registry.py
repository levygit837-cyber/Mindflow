from __future__ import annotations

from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.schemas.orchestration.orchestrator import AgentType


def test_researcher_registry_exposes_pinchtab_tools() -> None:
    registry = create_default_registry(MindFlowSandbox(root_dir="."))

    tool_names = [tool.name for tool in registry.get_tools_for_agent(AgentType.RESEARCHER)]

    assert "pinchtab_fleet" in tool_names
    assert "pinchtab_browser" in tool_names
    assert "web_scraper" in tool_names
