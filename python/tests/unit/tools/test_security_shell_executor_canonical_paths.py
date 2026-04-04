import pytest

from mindflow_backend.security.tools.shell_executor_v2 import ShellExecutorToolV2


class _FakeCanonicalShellExecutor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "success": True,
            "result": {
                "output": "ok",
                "stderr": "",
                "return_code": 0,
                "sandbox_type": "docker",
            },
        }


@pytest.mark.asyncio
async def test_security_shell_executor_v2_delegates_to_canonical_shell() -> None:
    tool = ShellExecutorToolV2(root_dir="/tmp/workspace", use_docker=True)
    fake = _FakeCanonicalShellExecutor()
    tool._canonical_tool = fake

    result = await tool.execute(command="echo ok", timeout=7)

    assert result["success"] is True
    assert result["result"]["sandbox_type"] == "docker"
    assert fake.calls == [
        {
            "command": "echo ok",
            "timeout": 7,
            "working_dir": "/tmp/workspace",
            "use_docker": True,
        }
    ]
