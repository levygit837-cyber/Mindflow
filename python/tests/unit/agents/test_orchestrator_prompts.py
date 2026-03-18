from mindflow_backend.agents.prompts.core.orchestrator import ORCHESTRATOR_CORE
from mindflow_backend.agents.prompts.specialized.agent_delegation import AGENT_DELEGATION


def test_orchestrator_core_mentions_workspace_scoped_file_exploration() -> None:
    lowered = ORCHESTRATOR_CORE.lower()

    assert "folder_path" in lowered
    assert "explor" in lowered
    assert "analyst" in lowered


def test_agent_delegation_prompt_mentions_workspace_root_for_file_exploration() -> None:
    lowered = AGENT_DELEGATION.lower()

    assert "workspace root" in lowered
    assert "folder_path" in lowered
    assert "files" in lowered
