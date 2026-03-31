"""Git Safety Hook — Bloqueia comandos git perigosos.

Adaptado de git safety features do Claude Code.
Verifica comandos bash que podem destruir dados git.
"""

from __future__ import annotations

import re
from typing import Any

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookPermissionBehavior
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Padrões de comandos git perigosos
_DANGEROUS_GIT_PATTERNS = [
    r"git\s+push\s+--force",
    r"git\s+push\s+-f\s",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-fd",
    r"git\s+clean\s+-f\s+-d",
    r"git\s+branch\s+-D",
    r"git\s+tag\s+-d",
    r"rm\s+-rf\s+\.git",
    r"rm\s+-rf\s+\.git/",
    r"git\s+filter-branch",
    r"git\s+reflog\s+expire",
    r"git\s+gc\s+--prune",
    r"git\s+worktree\s+remove\s+--force",
]

_DANGEROUS_COMPILED = [
    re.compile(p, re.IGNORECASE) for p in _DANGEROUS_GIT_PATTERNS
]


class GitSafetyHook:
    """Bloqueia comandos bash que podem destruir dados git."""

    @staticmethod
    async def execute(context: HookContext) -> HookResult:
        """Verifica se o comando é perigoso e bloqueia se necessário."""
        if not context.tool_input:
            return HookResult(
                event=context.hook_event_name,
                command="git_hook",
                status="success",
                behavior=HookPermissionBehavior.PASSTHROUGH,
            )

        # Extrair comando de diferentes formats de tool_input
        command = context.tool_input.get("command", "")
        if not command:
            return HookResult(
                event=context.hook_event_name,
                command="git_hook",
                status="success",
                behavior=HookPermissionBehavior.PASSTHROUGH,
            )

        # Verificar cada padrão perigoso
        for pattern in _DANGEROUS_COMPILED:
            match = pattern.search(command)
            if match:
                matched = match.group(0)
                _logger.warning(
                    "git_safety_blocked",
                    command=command[:200],
                    matched=matched,
                    session=context.session_id,
                )
                return HookResult(
                    event=context.hook_event_name,
                    command="git_hook",
                    status="success",
                    behavior=HookPermissionBehavior.DENY,
                    reason=f"Git safety hook blocked potentially destructive command: {matched}",
                    updated_input=context.tool_input,
                    hook_specific_output={
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Command '{matched}' can destroy git history or data",
                    },
                )

        return HookResult(
            event=context.hook_event_name,
            command="git_hook",
            status="success",
            behavior=HookPermissionBehavior.PASSTHROUGH,
        )