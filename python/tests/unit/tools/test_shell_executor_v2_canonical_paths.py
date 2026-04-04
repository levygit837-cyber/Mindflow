from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.system import shell_executor_v2


@pytest.mark.asyncio
async def test_shell_executor_v2_delegates_background_status_to_canonical_tool(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class _FakeCanonicalTool:
        async def get_background_status(self, process_id: str):
            calls["status_process_id"] = process_id
            return {"success": True, "status": "completed", "background_task_id": process_id}

    monkeypatch.setattr(shell_executor_v2, "ShellExecutorTool", lambda *args, **kwargs: _FakeCanonicalTool())

    tool = shell_executor_v2.ShellExecutorToolV2()
    result = await tool.get_background_status("bg-123")

    assert calls["status_process_id"] == "bg-123"
    assert result["success"] is True
    assert result["background_task_id"] == "bg-123"


@pytest.mark.asyncio
async def test_shell_executor_v2_delegates_background_kill_to_canonical_tool(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class _FakeCanonicalTool:
        async def kill_background_process(self, process_id: str):
            calls["kill_process_id"] = process_id
            return {"success": True, "status": "killed", "background_task_id": process_id}

    monkeypatch.setattr(shell_executor_v2, "ShellExecutorTool", lambda *args, **kwargs: _FakeCanonicalTool())

    tool = shell_executor_v2.ShellExecutorToolV2()
    result = await tool.kill_background_process("bg-456")

    assert calls["kill_process_id"] == "bg-456"
    assert result["success"] is True
    assert result["background_task_id"] == "bg-456"
