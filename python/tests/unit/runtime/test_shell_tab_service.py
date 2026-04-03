import asyncio
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_shell_tab_service_lifecycle(tmp_path: Path) -> None:
    from mindflow_backend.services.core.shell_tab_service import ShellTabService

    service = ShellTabService()
    session_id = "session-shell-1"

    created = await service.create_tab(session_id=session_id, cwd=str(tmp_path), title="repo-shell")
    assert created.session_id == session_id
    assert created.cwd == str(tmp_path)

    tabs = await service.list_tabs(session_id=session_id)
    assert len(tabs) == 1
    assert tabs[0].tab_id == created.tab_id

    executed = await service.exec_in_tab(
        session_id=session_id,
        tab_id=created.tab_id,
        command="pwd",
    )
    assert executed.state in {"completed", "running"}

    status = await service.get_tab_status(session_id=session_id, tab_id=created.tab_id)
    assert status.tab_id == created.tab_id
    assert status.cwd == str(tmp_path)
    assert "pwd" in (status.last_command or "")

    snapshot = await service.read_tab_buffer(session_id=session_id, tab_id=created.tab_id)
    assert str(tmp_path) in snapshot.stdout_buffer

    closed = await service.close_tab(session_id=session_id, tab_id=created.tab_id)
    assert closed.state == "terminated"


@pytest.mark.asyncio
async def test_shell_tab_service_emits_lifecycle_events(tmp_path: Path) -> None:
    from mindflow_backend.services.core.shell_tab_service import ShellTabService

    service = ShellTabService()
    session_id = "session-shell-events"
    received: list[dict] = []

    async def _consume_events() -> None:
        async for event in service.subscribe(session_id=session_id):
            received.append(event)
            if len(received) >= 4:
                break

    consumer = asyncio.create_task(_consume_events())
    await asyncio.sleep(0)

    created = await service.create_tab(session_id=session_id, cwd=str(tmp_path), title="events-shell")
    await service.exec_in_tab(session_id=session_id, tab_id=created.tab_id, command="printf ready")

    await asyncio.wait_for(consumer, timeout=5)

    assert received[0]["type"] == "snapshot"
    assert any(event["type"] == "shell_tab_created" for event in received)
    assert any(event["type"] == "shell_tab_running" for event in received)
    assert any(event["type"] == "shell_tab_completed" for event in received)


@pytest.mark.asyncio
async def test_shell_tab_service_uses_session_workspace_when_cwd_not_provided(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import mindflow_backend.services.core.shell_tab_service as module
    from mindflow_backend.services.core.shell_tab_service import ShellTabService

    session_workspace = tmp_path / "isolated-workspace"
    session_workspace.mkdir()

    class _FakeRuntimeStateService:
        async def save_session_state(self, session_id: str, state: dict) -> dict:
            return state

        async def load_session_state(self, session_id: str) -> dict | None:
            return {
                "workspace": {
                    "session": {
                        "workspace_root": str(session_workspace),
                        "workspace_path": str(session_workspace),
                    }
                }
            }

        async def list_session_states(self) -> list[dict]:
            return []

    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: _FakeRuntimeStateService(), raising=False)

    service = ShellTabService()
    created = await service.create_tab(session_id="shell-default", title="default-shell")

    assert created.cwd == str(session_workspace)
    assert created.workspace_root == str(session_workspace)
