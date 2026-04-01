"""PluginLoader — Carrega hooks de plugins (hooks.json)."""

from __future__ import annotations

import json
from pathlib import Path

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.infra.logging import get_logger

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
    hooks_path = Path(plugin_dir) / "hooks.json"
    if not hooks_path.exists():
        return 0

    try:
        with open(hooks_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _logger.error("plugin_hooks_load_error", plugin=plugin_name, error=str(exc))
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