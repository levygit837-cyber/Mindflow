"""PreToolUse Handler — Executado ANTES de tool execution.

Equivalente de executePreToolHooks em src/utils/hooks.ts.
Pode modificar input ou bloquear a execução da tool.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent


class PreToolUseHandler:
    """Handler para hooks PreToolUse — equivalente de runPreToolUseHooks em src/services/tools/toolHooks.ts."""

    @staticmethod
    async def execute(
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
        session_id: str,
        *,
        cwd: str | None = None,
        permission_mode: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks PreToolUse para uma tool específica."""
        manager = HookManager.get_instance()
        async for result in manager.execute_pre_tool(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            session_id=session_id,
            cwd=cwd,
            permission_mode=permission_mode,
            timeout=timeout,
        ):
            yield result