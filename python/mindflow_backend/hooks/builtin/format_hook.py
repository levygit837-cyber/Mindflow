"""Format Hook — Auto-formatação de código após tool edits.

Adaptado de src/hooks/toolPermission/ do Claude Code.
Executa formatação de código após FileEdit/FileWrite tools.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Mapeamento de extensões para comandos de formatação
_FORMATTERS = {
    ".py": ["ruff", "format"],
    ".ts": ["prettier", "--write"],
    ".tsx": ["prettier", "--write"],
    ".js": ["prettier", "--write"],
    ".jsx": ["prettier", "--write"],
    ".rs": ["rustfmt"],
    ".go": ["gofmt", "-w"],
    ".java": ["google-java-format", "-i"],
    ".cs": ["dotnet", "format"],
}


class FormatHook:
    """Executa formatação de código após FileEdit/FileWrite tools."""

    @staticmethod
    async def execute(context: HookContext) -> HookResult:
        """Formata o arquivo editado pelo tool."""
        if not context.tool_input:
            return HookResult(
                event=context.hook_event_name,
                command="format_hook",
                status="success",
            )

        file_path = context.tool_input.get("file_path", "")
        if not file_path:
            return HookResult(
                event=context.hook_event_name,
                command="format_hook",
                status="success",
            )

        # Detectar formatter apropriado
        import os
        _, ext = os.path.splitext(file_path)
        formatter_cmd = _FORMATTERS.get(ext.lower())

        if not formatter_cmd:
            # Sem formatter disponível — sucesso silencioso
            return HookResult(
                event=context.hook_event_name,
                command="format_hook",
                status="success",
            )

        try:
            full_cmd = formatter_cmd + [file_path]
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)

            if proc.returncode != 0:
                _logger.warning(
                    "format_hook_failed",
                    file=file_path,
                    cmd=" ".join(formatter_cmd),
                    error=stderr.decode() if stderr else f"Exit code {proc.returncode}",
                )
                # Falha de formatação não deve bloquear — apenas logar
                return HookResult(
                    event=context.hook_event_name,
                    command="format_hook",
                    status="success",
                    error=f"Format failed: {stderr.decode()[:200] if stderr else 'unknown'}",
                )

            return HookResult(
                event=context.hook_event_name,
                command="format_hook",
                status="success",
            )
        except FileNotFoundError:
            # Formatter não instalado — sucesso silencioso
            return HookResult(
                event=context.hook_event_name,
                command="format_hook",
                status="success",
            )
        except Exception as exc:
            _logger.warning("format_hook_error", file=file_path, error=str(exc))
            return HookResult(
                event=context.hook_event_name,
                command="format_hook",
                status="success",
                error=str(exc),
            )