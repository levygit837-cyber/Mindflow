"""Manifest loading and component resolution for plugins."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mindflow_backend.plugins.models import PluginManifest


DEFAULT_COMMANDS_DIR = "commands"
DEFAULT_AGENTS_DIR = "agents"
DEFAULT_SKILLS_DIR = "skills"
DEFAULT_HOOKS_PATHS = ("hooks/hooks.json", "hooks.json")


def load_plugin_manifest(plugin_root: Path) -> PluginManifest:
    """Load the plugin manifest or derive a minimal one from the directory name."""
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        return PluginManifest(name=plugin_root.name, raw={})

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    return PluginManifest(
        name=raw["name"],
        version=raw.get("version", "0.0.0"),
        description=raw.get("description", ""),
        author=_extract_author(raw.get("author")),
        commands=raw.get("commands"),
        agents=raw.get("agents"),
        skills=raw.get("skills"),
        hooks=raw.get("hooks"),
        mcp_servers=raw.get("mcpServers"),
        settings_path=raw.get("settings"),
        raw=raw,
    )


def _extract_author(author: Any) -> str | None:
    if isinstance(author, str):
        return author
    if isinstance(author, dict):
        name = author.get("name")
        if name:
            return str(name)
    return None


def resolve_component_paths(
    plugin_root: Path,
    configured_value: str | list[str] | None,
    default_directory: str,
) -> list[Path]:
    """Resolve component paths using Claude-style manifest semantics."""
    if configured_value is None:
        default_path = plugin_root / default_directory
        return [default_path] if default_path.exists() else []

    entries = configured_value if isinstance(configured_value, list) else [configured_value]
    paths: list[Path] = []
    for entry in entries:
        candidate = plugin_root / str(entry).removeprefix("./")
        if candidate.exists():
            paths.append(candidate)
    return paths


def resolve_hook_configs(
    plugin_root: Path,
    configured_value: str | list[str] | dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Resolve hook config objects from inline or file-based declarations."""
    if isinstance(configured_value, dict):
        return [configured_value]

    if configured_value is None:
        configs: list[dict[str, Any]] = []
        for relative_path in DEFAULT_HOOKS_PATHS:
            candidate = plugin_root / relative_path
            if candidate.exists():
                configs.append(json.loads(candidate.read_text(encoding="utf-8")))
        return configs

    configs = []
    entries = configured_value if isinstance(configured_value, list) else [configured_value]
    for entry in entries:
        candidate = plugin_root / str(entry).removeprefix("./")
        if candidate.exists():
            configs.append(json.loads(candidate.read_text(encoding="utf-8")))
    return configs
