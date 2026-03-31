from __future__ import annotations

from pathlib import Path

import pytest

from mindflow_backend.agents.specialists.factories import create_review_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.filesystem import FileWriteTool
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.agents.tools.system import ShellExecutorTool
from mindflow_backend.infra.config import get_settings
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode


@pytest.fixture(autouse=True)
def _secure_sandbox_flag() -> None:
    settings = get_settings()
    original = dict(settings.feature_flags)
    settings.feature_flags["sandbox_secure_runtime"] = True
    try:
        yield
    finally:
        settings.feature_flags.clear()
        settings.feature_flags.update(original)


def test_registry_respects_agent_policy_and_removes_write_tools(tmp_path: Path) -> None:
    sandbox = MindFlowSandbox(root_dir=str(tmp_path), read_only=True)
    registry = create_default_registry(sandbox)

    reviewer = create_review_agent()
    tools = registry.get_tools_for_agent(reviewer)
    tool_names = {tool.name for tool in tools}

    assert "read_file" in tool_names
    assert "shell_execute" in tool_names

    assert "write_file" not in tool_names
    assert "edit_file" not in tool_names
    assert "delete_file" not in tool_names
    assert "mkdir" not in tool_names
    assert "process_manager" not in tool_names
    assert "shell_tab_open" not in tool_names


@pytest.mark.asyncio
async def test_file_write_rejects_absolute_path_outside_workspace(tmp_path: Path) -> None:
    tool = FileWriteTool()
    tool.root_dir = str(tmp_path)
    tool.sandbox_mode = SandboxMode.FULL

    outside = tmp_path.parent / "escaped.txt"
    result = await tool.execute(file_path=str(outside), content="blocked")

    assert not result["success"]
    assert "workspace" in (result["error"] or "").lower()
    assert not outside.exists()


@pytest.mark.asyncio
async def test_shell_execute_defaults_to_root_dir_and_drops_host_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_TEST_VAR", "top-secret-value")

    tool = ShellExecutorTool()
    tool.root_dir = str(tmp_path)
    tool.sandbox_mode = SandboxMode.FULL

    result = await tool.execute(command="pwd && printf \"$SECRET_TEST_VAR\"")

    assert result["success"], result
    output = result["result"]["output"]
    assert str(tmp_path) in output
    assert "top-secret-value" not in output


@pytest.mark.asyncio
async def test_shell_execute_blocks_write_commands_in_read_only_mode(tmp_path: Path) -> None:
    tool = ShellExecutorTool()
    tool.root_dir = str(tmp_path)
    tool.sandbox_mode = SandboxMode.READ_ONLY

    target = tmp_path / "blocked.txt"
    result = await tool.execute(command="touch blocked.txt")

    assert not result["success"]
    assert "read-only" in (result["error"] or "").lower()
    assert not target.exists()
