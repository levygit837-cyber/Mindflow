from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_shell_tab_service_rejects_cwd_outside_workspace(tmp_path: Path) -> None:
    from mindflow_backend.services.core.shell_tab_service import ShellTabService

    service = ShellTabService()

    with pytest.raises(ValueError, match="workspace"):
        await service.create_tab(
            session_id="session-shell-secure",
            cwd=str(tmp_path.parent),
            title="invalid-shell",
            workspace_root=str(tmp_path),
            secure_mode=True,
        )


@pytest.mark.asyncio
async def test_shell_tab_service_blocks_write_commands_in_read_only_mode(tmp_path: Path) -> None:
    from mindflow_backend.services.core.shell_tab_service import ShellTabService

    service = ShellTabService()
    created = await service.create_tab(
        session_id="session-shell-readonly",
        cwd=str(tmp_path),
        title="readonly-shell",
        workspace_root=str(tmp_path),
        read_only=True,
        secure_mode=True,
    )

    executed = await service.exec_in_tab(
        session_id=created.session_id,
        tab_id=created.tab_id,
        command="touch should_not_exist.txt",
    )

    assert executed.state == "failed"
    assert "read-only" in executed.stderr_buffer.lower()
    assert not (tmp_path / "should_not_exist.txt").exists()
