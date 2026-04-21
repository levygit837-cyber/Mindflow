"""Tests for plugin-backed slash commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mindflow_backend.commands.executor import CommandExecutor
from mindflow_backend.commands.loader import CommandLoader
from mindflow_backend.commands.registry import CommandRegistry
from mindflow_backend.plugins.manager import PluginManager
from mindflow_backend.plugins.models import PluginScope
from mindflow_backend.plugins.state_store import PluginStateStore


def _write_markdown_plugin(root: Path) -> None:
    plugin_dir = root / "docs-plugin"
    (plugin_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "docs-plugin", "version": "1.0.0"})
    )
    (plugin_dir / "commands").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "commands" / "deploy.md").write_text(
        "---\n"
        "name: deploy\n"
        "description: Deploy the current service\n"
        "---\n\n"
        "Deploy target: $ARGUMENTS\n"
    )

    skill_dir = plugin_dir / "skills" / "summary"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: summary\n"
        "description: Summarize the active changes\n"
        "---\n\n"
        "Summary target: $ARGUMENTS\n"
    )


@pytest.mark.asyncio
async def test_command_loader_registers_markdown_plugin_commands(tmp_path: Path) -> None:
    plugin_root = tmp_path / "project-plugins"
    state_path = tmp_path / "plugin-state.json"
    _write_markdown_plugin(plugin_root)
    state_path.write_text(json.dumps({"enabled_plugins": ["docs-plugin"]}))

    manager = PluginManager(
        plugin_roots={PluginScope.PROJECT: plugin_root},
        state_store=PluginStateStore(state_paths={PluginScope.PROJECT: state_path}),
    )
    registry = CommandRegistry()
    loader = CommandLoader(registry=registry, plugin_manager=manager)

    loaded = await loader.load_all_commands(cwd=str(tmp_path))

    assert loaded >= 2
    assert registry.has("docs-plugin:deploy")
    assert registry.has("docs-plugin:summary")

    executor = CommandExecutor(registry=registry)
    result = await executor.execute(
        "docs-plugin:deploy",
        ["production"],
        session_id="session-cmd",
    )

    assert result.success is True
    assert "Deploy target: production" in result.message
