import pytest

from omnimind_backend.agents.safe_backend import ExecuteResult, SafeBackend


class MockBackend:
    def __init__(self) -> None:
        self.commands: list[str] = []

    async def execute(self, command: str) -> ExecuteResult:
        self.commands.append(command)
        return ExecuteResult(stdout="ok", stderr="", exitCode=0)


@pytest.mark.asyncio
async def test_blocks_rm_command() -> None:
    inner = MockBackend()
    backend = SafeBackend(inner)

    result = await backend.execute("rm -rf /tmp/test")

    assert result.exitCode == 1
    assert "BLOCKED" in result.stderr
    assert inner.commands == []


@pytest.mark.asyncio
async def test_allows_safe_command() -> None:
    inner = MockBackend()
    backend = SafeBackend(inner)

    result = await backend.execute("git status")

    assert result.exitCode == 0
    assert inner.commands == ["git status"]
