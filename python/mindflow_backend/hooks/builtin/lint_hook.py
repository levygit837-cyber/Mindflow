"""Lint Hook — Executa linter após tool edits."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Mapeamento de extensões para comandos de linting
_LINTERS = {
    ".py": ["ruff", "check"],
    ".ts": ["eslint", "--no-warn-ignored"],
    ".tsx": ["eslint", "--no-warn-ignored"],
    ".js": ["eslint", "--no-warn-ignored"],
    ".jsx": ["eslint", "--no-warn-ignored"],
    ".go": ["golangci-lint", "run"],
    ".rs": ["clippy-driver"],
    ".java": ["checkstyle"],
}


class LintHook:
    """Executa linter após FileEdit/FileWrite tools."""

    @staticmethod
    async def execute(context: HookContext) -> HookResult:
        """Roda o linter no arquivo editado."""
        if not context.tool_input:
            return HookResult(
                event=context.hook_event_name,
                command="lint_hook",
                status="success",
            )

        file_path = context.tool_input.get("file_path", "")
        if not file_path:
            return HookResult(
                event=context.hook_event_name,
                command="lint_hook",
                status="success",
            )

        _, ext = os.path.splitext(file_path)
        linter_cmd = _LINTERS.get(ext.lower())

        if not linter_cmd:
            return HookResult(
                event=context.hook_event_name,
                command="lint_hook",
                status="success",
            )

        try:
            full_cmd = linter_cmd + [file_path]
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)

            output = (stdout.decode() + stderr.decode()).strip()

            if proc.returncode != 0 and output:
                # Linter encontrou issues — adicionar como contexto
                return HookResult(
                    event=context.hook_event_name,
                    command="lint_hook",
                    status="success",
                    add_context=f"Lint issues in {file_path}:\n{output[:1000]}",
                    hook_specific_output={
                        "hookEventName": "PostToolUse",
                        "additionalContext": f"Lint issues in {file_path}:\n{output[:1000]}",
                    },
                )

            return HookResult(
                event=context.hook_event_name,
                command="lint_hook",
                status="success",
            )
        except FileNotFoundError:
            return HookResult(
                event=context.hook_event_name,
                command="lint_hook",
                status="success",
            )
        except Exception as exc:
            _logger.warning("lint_hook_error", file=file_path, error=str(exc))
            return HookResult(
                event=context.hook_event_name,
                command="lint_hook",
                status="success",
                error=str(exc),
            )