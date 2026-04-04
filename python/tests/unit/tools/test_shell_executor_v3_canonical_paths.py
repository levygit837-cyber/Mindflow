from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.system import shell_executor_v3
from mindflow_backend.schemas.tools.context import ToolContext


def _make_fake_legacy_builder(calls: dict[str, object], payload: dict[str, object]):
    class _FakeTool:
        async def execute(self, **kwargs):
            calls["kwargs"] = kwargs
            return {"success": True, "result": payload}

    def _builder(tool_cls, context):
        calls["tool_cls"] = tool_cls.__name__
        calls["context"] = context
        return _FakeTool()

    return _builder


@pytest.mark.asyncio
async def test_shell_executor_v3_delegates_to_canonical_tool(monkeypatch, tmp_path) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        shell_executor_v3,
        "build_legacy_tool",
        _make_fake_legacy_builder(
            calls,
            {
                "output": "MindFlow\n",
                "stderr": "",
                "return_code": 0,
                "pid": 42,
                "working_dir": str(tmp_path),
                "execution_time": 0.1,
                "timeout": False,
                "semantic_type": "system",
                "security_level": "safe",
            },
        ),
        raising=False,
    )

    result = await shell_executor_v3.shell_execute(
        shell_executor_v3.ShellExecutorInput(
            command="echo 'MindFlow'",
            timeout=12,
            working_dir=str(tmp_path),
            capture_output=False,
            shell=True,
            check_return_code=True,
        ),
        ToolContext(root_dir=str(tmp_path), metadata={}),
    )

    assert calls["tool_cls"] == "ShellExecutorTool"
    assert calls["kwargs"] == {
        "command": "echo 'MindFlow'",
        "timeout": 12,
        "working_dir": str(tmp_path),
        "capture_output": False,
        "shell": True,
        "check_return_code": True,
    }
    assert result["success"] is True
    assert result["output"] == "MindFlow\n"
