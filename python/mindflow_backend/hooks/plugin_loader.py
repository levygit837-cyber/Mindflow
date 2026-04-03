"""PluginLoader — Carrega hooks de plugins (hooks.json)."""

from __future__ import annotations

import json
from pathlib import Path

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.plugins.manifest import DEFAULT_HOOKS_PATHS

_logger = get_logger(__name__)


def load_plugin_hooks(plugin_name: str, plugin_dir: str) -> int:
    """Carrega hooks de um plugin.

    O plugin deve ter um arquivo hooks.json no formato:
    {
      "description": "Plugin hooks",
      "hooks": {
        "PreToolUse": [
          {"matcher": "Bash", "hooks": [{"type": "command", "command": "..."}]}
        ]
      }
    }
    """
    plugin_root = Path(plugin_dir)
    config: dict[str, object] | None = None

    for relative_path in DEFAULT_HOOKS_PATHS:
        hooks_path = plugin_root / relative_path
        if not hooks_path.exists():
            continue
        try:
            with open(hooks_path, encoding="utf-8") as file_handle:
                config = json.load(file_handle)
            break
        except (json.JSONDecodeError, OSError) as exc:
            _logger.error(
                "plugin_hooks_load_error",
                plugin=plugin_name,
                path=str(hooks_path),
                error=str(exc),
            )
            return 0

    if config is None:
        return 0

    hooks_config = config.get("hooks", {})
    if not hooks_config:
        return 0

    manager = HookManager.get_instance()
    manager.register_plugin_commands(plugin_name, hooks_config)

    count = sum(
        len(matcher.get("hooks", []))
        for matchers in hooks_config.values()
        for matcher in (matchers if isinstance(matchers, list) else [])
    )

    _logger.info("plugin_hooks_loaded", plugin=plugin_name, count=count)
    return count
