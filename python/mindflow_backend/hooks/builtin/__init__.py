"""Builtin Hooks — Auto-registro de hooks pré-construídos para MindFlow.

Adaptados de src/hooks/ do Claude Code:
- format_hook.py: Auto-formatação de código
- lint_hook.py: Execução de linter
- test_hook.py: Execução de testes pós-tool
- git_hook.py: Git safety (bloqueia comandos perigosos)
"""

from __future__ import annotations

import logging

from mindflow_backend.hooks.builtin.format_hook import FormatHook
from mindflow_backend.hooks.builtin.lint_hook import LintHook
from mindflow_backend.hooks.builtin.test_hook import TestHook
from mindflow_backend.hooks.builtin.git_hook import GitSafetyHook

logger = logging.getLogger(__name__)

__all__ = [
    "FormatHook",
    "LintHook",
    "TestHook",
    "GitSafetyHook",
    "register_builtin_hooks",
]


def register_builtin_hooks() -> int:
    """Registra todos os builtin hooks. Retorna número de hooks registrados.

    Chamado automaticamente na inicialização do sistema via
    load_hooks_on_startup() em settings.py.
    """
    from mindflow_backend.hooks.manager import HookManager
    from mindflow_backend.hooks.types import HookEvent

    manager = HookManager.get_instance()
    count = 0

    # ── Format hook — PostToolUse para Write|Edit ──
    manager.register_command(
        HookEvent.POST_TOOL_USE,
        "Write|Edit",
        "jq -r '.tool_input.file_path // .tool_response.filePath' 2>/dev/null | "
        "{ read -r f && [ -n \"$f\" ] && black \"$f\" 2>/dev/null || true; }",
        timeout=30,
    )
    count += 1

    # ── Lint hook — PostToolUse para Write|Edit ──
    manager.register_command(
        HookEvent.POST_TOOL_USE,
        "Write|Edit",
        "jq -r '.tool_input.file_path // .tool_response.filePath' 2>/dev/null | "
        "{ read -r f && [ -n \"$f\" ] && ruff check \"$f\" 2>/dev/null || true; }",
        timeout=30,
    )
    count += 1

    # ── Git safety hook — PreToolUse para Bash ──
    manager.register_command(
        HookEvent.PRE_TOOL_USE,
        "Bash",
        "jq -r '.tool_input.command' 2>/dev/null | "
        "grep -qE 'git\\s+(push\\s+--force|reset\\s+--hard|clean\\s+-fd)' && "
        "echo '{\"behavior\":\"deny\",\"reason\":\"Dangerous git command blocked\"}' || "
        "true",
        timeout=10,
    )
    count += 1

    logger.info("builtin_hooks_registered", count=count)
    return count