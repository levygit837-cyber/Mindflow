from unittest.mock import AsyncMock

import pytest

from mindflow_backend.agents.tools.callable import shell as callable_shell
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
@pytest.mark.parametrize(
    ("impl_name", "input_name", "tool_name", "input_kwargs", "payload", "expected_kwargs"),
    [
        (
            "shell_executor_impl",
            "ShellExecutorInput",
            "ShellExecutorTool",
            {
                "command": "echo 'MindFlow'",
                "timeout": 12,
                "working_dir": "workspace",
                "capture_output": False,
                "shell": True,
                "check_return_code": True,
            },
            {"marker": "shell", "timed_out": False},
            {
                "command": "echo 'MindFlow'",
                "timeout": 12,
                "working_dir": "workspace",
                "capture_output": False,
                "shell": True,
                "check_return_code": True,
            },
        ),
        (
            "system_info_impl",
            "SystemInfoInput",
            "SystemInfoTool",
            {
                "info_type": "software",
                "include_sensitive": True,
            },
            {"marker": "system"},
            {
                "info_type": "software",
                "include_sensitive": True,
            },
        ),
        (
            "process_manager_impl",
            "ProcessManagerInput",
            "ProcessManagerTool",
            {
                "action": "kill",
                "pid": 1234,
                "signal_name": "SIGKILL",
                "filter_name": "python",
                "filter_user": "mindflow",
            },
            {"marker": "process"},
            {
                "action": "kill",
                "pid": 1234,
                "signal": "SIGKILL",
                "filter_name": "python",
                "filter_user": "mindflow",
            },
        ),
    ],
)
async def test_callable_system_impls_delegate_to_canonical_tools(
    monkeypatch,
    tmp_path,
    impl_name,
    input_name,
    tool_name,
    input_kwargs,
    payload,
    expected_kwargs,
) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        callable_shell,
        "build_legacy_tool",
        _make_fake_legacy_builder(calls, payload),
        raising=False,
    )
    monkeypatch.setattr(
        callable_shell,
        "deny_if_permission_blocked",
        AsyncMock(return_value=None),
        raising=False,
    )

    impl = getattr(callable_shell, impl_name)
    input_cls = getattr(callable_shell, input_name)
    context = ToolContext(metadata={})
    if input_kwargs.get("working_dir"):
        (tmp_path / input_kwargs["working_dir"]).mkdir()
        context = ToolContext(root_dir=str(tmp_path), metadata={})

    result = await impl(input_cls(**input_kwargs), context)

    assert calls["tool_cls"] == tool_name
    assert calls["kwargs"] == expected_kwargs
    assert result.success is True
    for key, value in payload.items():
        assert result.data[key] == value
