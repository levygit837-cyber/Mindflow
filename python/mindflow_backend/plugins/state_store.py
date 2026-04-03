"""Persistence for plugin enabled and disabled state by scope."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from mindflow_backend.plugins.models import PluginScope


@dataclass(frozen=True, slots=True)
class PluginState:
    """Persisted state for one scope."""

    enabled_plugins: list[str] = field(default_factory=list)
    disabled_plugins: list[str] = field(default_factory=list)
    plugin_configs: dict[str, dict] = field(default_factory=dict)


class PluginStateStore:
    """Load and save plugin state files for each scope."""

    def __init__(
        self,
        state_paths: dict[PluginScope, Path] | None = None,
    ) -> None:
        self._explicit_paths = state_paths or {}

    def load_state(self, scope: PluginScope, cwd: str | None = None) -> PluginState:
        """Load state for a scope."""
        path = self.get_state_path(scope, cwd=cwd)
        if not path.exists():
            return PluginState()

        raw = json.loads(path.read_text(encoding="utf-8"))
        return PluginState(
            enabled_plugins=list(raw.get("enabled_plugins", [])),
            disabled_plugins=list(raw.get("disabled_plugins", [])),
            plugin_configs=dict(raw.get("plugin_configs", {})),
        )

    def save_state(
        self,
        scope: PluginScope,
        state: PluginState,
        cwd: str | None = None,
    ) -> None:
        """Save state for a scope."""
        path = self.get_state_path(scope, cwd=cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "enabled_plugins": state.enabled_plugins,
                    "disabled_plugins": state.disabled_plugins,
                    "plugin_configs": state.plugin_configs,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def get_state_path(self, scope: PluginScope, cwd: str | None = None) -> Path:
        """Resolve the state file path for a scope."""
        if scope in self._explicit_paths:
            return self._explicit_paths[scope]

        current_dir = Path(cwd or ".").resolve()
        if scope == PluginScope.USER:
            return Path.home() / ".mindflow" / "plugins.json"
        if scope == PluginScope.PROJECT:
            return current_dir / ".mindflow" / "plugins.json"
        if scope == PluginScope.LOCAL:
            return current_dir / ".mindflow" / "local" / "plugins.json"
        return Path("/etc/mindflow/plugins.json")
