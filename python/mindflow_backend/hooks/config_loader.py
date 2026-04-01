"""ConfigLoader — Carrega hooks de settings.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.types import HookEvent
from mindflow_backend.hooks.result import HookCommand
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def load_hooks_from_settings(settings_path: str) -> int:
    """Carrega hooks de settings.yaml.

    Formato esperado:
    hooks:
      PreToolUse:
        - matcher: "Bash"
          hooks:
            - type: command
              command: "jq -r '.tool_input.command' >> ~/.mindflow/bash-log.txt"
              timeout: 30
      PostToolUse:
        - matcher: "Write|Edit"
          hooks:
            - type: command
              command: "prettier --write $FILE"
    """
    path = Path(settings_path)
    if not path.exists():
        _logger.warning("settings_file_not_found", path=str(path))
        return 0

    with open(path) as f:
        settings = yaml.safe_load(f)

    if not settings:
        return 0

    hooks_config = settings.get("hooks", {})
    if not hooks_config:
        return 0

    manager = HookManager.get_instance()
    count = 0

    for event_str, matchers in hooks_config.items():
        try:
            event = HookEvent(event_str)
        except ValueError:
            _logger.warning("unknown_hook_event", event=event_str)
            continue

        if not isinstance(matchers, list):
            continue

        for matcher_config in matchers:
            matcher = matcher_config.get("matcher")
            hooks_list = matcher_config.get("hooks", [])

            for hook_dict in hooks_list:
                cmd = HookCommand(
                    type=hook_dict.get("type", "command"),
                    command=hook_dict.get("command"),
                    timeout=hook_dict.get("timeout"),
                )
                manager.registry.register_config_hook(event, matcher, cmd)
                count += 1

    _logger.info("hooks_loaded_from_settings", path=str(path), count=count)
    return count