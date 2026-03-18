from __future__ import annotations

from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.schemas.orchestration.orchestrator import AgentType


def test_code_analysis_registry_prefers_gitnexus_before_filesystem() -> None:
    registry = create_default_registry(MindFlowSandbox(root_dir="."))
    analyst_tools = registry.get_tools_for_agent(AgentType.ANALYST)
    tool_names = [tool.name for tool in analyst_tools]

    ordered_names = [
        "gitnexus_status",
        "gitnexus_query",
        "gitnexus_context",
        "gitnexus_impact",
        "read_file",
        "grep_search",
        "glob_search",
    ]

    indices = [tool_names.index(name) for name in ordered_names]
    assert indices == sorted(indices)

    researcher_tool_names = [tool.name for tool in registry.get_tools_for_agent(AgentType.RESEARCHER)]
    assert all(not name.startswith("gitnexus_") for name in researcher_tool_names)
