from __future__ import annotations

from pathlib import Path

import pytest


class _FakeRuntimeStateService:
    def __init__(self) -> None:
        self.saved: dict[str, dict] = {}

    async def save_session_state(self, session_id: str, state: dict) -> dict:
        current = self.saved.get(session_id, {})
        merged = {**current, **state}
        self.saved[session_id] = merged
        return merged

    async def load_session_state(self, session_id: str) -> dict | None:
        return self.saved.get(session_id)

    async def list_session_states(self) -> list[dict]:
        return [
            {"session_id": session_id, **state}
            for session_id, state in self.saved.items()
        ]


class _FakeProcess:
    def __init__(self, *, pid: int = 4321, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> None:
        self.pid = pid
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_shell_tab_service_persists_and_rehydrates_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import mindflow_backend.services.core.shell_tab_service as module
    from mindflow_backend.services.core.shell_tab_service import ShellTabService
    from mindflow_backend.schemas.tools.shell_tabs import ShellTabState

    fake_runtime_state = _FakeRuntimeStateService()
    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: fake_runtime_state, raising=False)

    first_service = ShellTabService()
    tab = await first_service.create_tab(
        session_id="shell-session",
        cwd=str(tmp_path),
        title="shell",
        workspace_root=str(tmp_path),
        secure_mode=True,
    )

    assert fake_runtime_state.saved["shell-session"]["shell_tabs"]["tabs"][tab.tab_id]["tab"]["title"] == "shell"

    second_service = ShellTabService()
    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: fake_runtime_state, raising=False)

    restored_tabs = await second_service.list_tabs("shell-session")
    restored_status = await second_service.get_tab_status("shell-session", tab.tab_id)

    assert len(restored_tabs) == 1
    assert restored_tabs[0].tab_id == tab.tab_id
    assert restored_status.state == ShellTabState.IDLE


@pytest.mark.asyncio
async def test_shell_tab_service_persists_exec_updates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import mindflow_backend.services.core.shell_tab_service as module
    from mindflow_backend.services.core.shell_tab_service import ShellTabService
    from mindflow_backend.schemas.tools.shell_tabs import ShellTabState

    fake_runtime_state = _FakeRuntimeStateService()
    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: fake_runtime_state, raising=False)

    async def _fake_create_subprocess_shell(*args, **kwargs) -> _FakeProcess:
        return _FakeProcess(stdout=b"hello\n")

    monkeypatch.setattr(module.asyncio, "create_subprocess_shell", _fake_create_subprocess_shell)

    service = ShellTabService()
    tab = await service.create_tab(
        session_id="shell-update-session",
        cwd=str(tmp_path),
        title="shell",
        workspace_root=str(tmp_path),
        secure_mode=True,
    )

    executed = await service.exec_in_tab(
        session_id=tab.session_id,
        tab_id=tab.tab_id,
        command="echo hello",
    )

    assert executed.state == ShellTabState.COMPLETED
    assert fake_runtime_state.saved["shell-update-session"]["shell_tabs"]["tabs"][tab.tab_id]["tab"]["last_command"] == "echo hello"
    assert fake_runtime_state.saved["shell-update-session"]["shell_tabs"]["tabs"][tab.tab_id]["tab"]["stdout_buffer"].strip() == "hello"
