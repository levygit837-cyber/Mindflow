"""PostToolUse Handler — Executado DEPOIS de tool execution.

Equivalente de executePostToolHooks em src/utils/hooks.ts.
Pode modificar output ou adicionar contexto.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult


class PostToolUseHandler:
    """Handler para hooks PostToolUse."""

    @staticmethod
    async def execute(
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
        tool_response: Any,
        session_id: str,
        *,
        cwd: str | None = None,
        permission_mode: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        async for result in manager.execute_post_tool(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            tool_response=tool_response,
            session_id=session_id,
            cwd=cwd,
            permission_mode=permission_mode,
            timeout=timeout,
        ):
            yield result