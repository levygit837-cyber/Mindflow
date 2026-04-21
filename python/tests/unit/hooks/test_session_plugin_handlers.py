"""Tests for plugin lifecycle integration in session hook handlers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mindflow_backend.hooks import HookEvent
from mindflow_backend.hooks.handlers.session_end import SessionEndHandler
from mindflow_backend.hooks.handlers.session_start import SessionStartHandler
from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.plugins.manager import PluginManager
from mindflow_backend.plugins.models import PluginScope
from mindflow_backend.plugins.state_store import PluginStateStore
import mindflow_backend.plugins.manager as plugin_manager_module


def _write_plugin(root: Path, plugin_id: str, hooks: dict[str, object]) -> None:
    plugin_dir = root / plugin_id
    (plugin_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": plugin_id, "version": "1.0.0"})
    )
    (plugin_dir / "hooks").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "hooks" / "hooks.json").write_text(json.dumps({"hooks": hooks}))


@pytest.fixture
def plugin_manager_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PluginManager:
    plugin_root = tmp_path / "project-plugins"
    state_path = tmp_path / "plugin-state.json"

    manager = PluginManager(
        plugin_roots={PluginScope.PROJECT: plugin_root},
        state_store=PluginStateStore(state_paths={PluginScope.PROJECT: state_path}),
    )

    HookManager.get_instance().registry.clear_all()
    monkeypatch.setattr(plugin_manager_module, "_plugin_manager", manager)

    async def _empty_memory_files(self, cwd: str) -> list[object]:
        return []

    monkeypatch.setattr(
        "mindflow_backend.agents.prompts.layers.memory_loader.MemoryFileLoader.load_all",
        _empty_memory_files,
    )

    return manager


@pytest.mark.asyncio
async def test_session_start_handler_activates_plugin_hooks(
    plugin_manager_fixture: PluginManager,
    tmp_path: Path,
) -> None:
    _write_plugin(
        tmp_path / "project-plugins",
        "session-plugin",
        hooks={
            "SessionStart": [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": "echo session-start"}],
                }
            ]
        },
    )
    (tmp_path / "plugin-state.json").write_text(
        json.dumps({"enabled_plugins": ["session-plugin"]})
    )

    results = [
        result
        async for result in SessionStartHandler.execute(
            session_id="session-handler",
            cwd=str(tmp_path),
        )
    ]

    snapshot = plugin_manager_fixture.get_session_snapshot("session-handler")

    assert snapshot is not None
    assert len(snapshot.plugins) == 1
    assert any(result.command == "echo session-start" for result in results)


@pytest.mark.asyncio
async def test_session_end_handler_cleans_up_session_scoped_plugin_hooks(
    plugin_manager_fixture: PluginManager,
    tmp_path: Path,
) -> None:
    _write_plugin(
        tmp_path / "project-plugins",
        "session-plugin",
        hooks={
            "SessionEnd": [
                {
                    "matcher": "shutdown",
                    "hooks": [{"type": "command", "command": "echo session-end"}],
                }
            ]
        },
    )
    (tmp_path / "plugin-state.json").write_text(
        json.dumps({"enabled_plugins": ["session-plugin"]})
    )

    await plugin_manager_fixture.activate_session("session-cleanup", cwd=str(tmp_path))

    before = HookManager.get_instance().registry.get_hooks_for_event(
        HookEvent.SESSION_END,
        session_id="session-cleanup",
        match_query="shutdown",
    )
    results = [
        result
        async for result in SessionEndHandler.execute(
            session_id="session-cleanup",
            reason="shutdown",
            cwd=str(tmp_path),
        )
    ]
    after = HookManager.get_instance().registry.get_hooks_for_event(
        HookEvent.SESSION_END,
        session_id="session-cleanup",
        match_query="shutdown",
    )

    assert len(before) == 1
    assert any(result.command == "echo session-end" for result in results)
    assert after == []
    assert plugin_manager_fixture.get_session_snapshot("session-cleanup") is None
