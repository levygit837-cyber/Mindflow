"""PostToolFailure Handler — Executado quando tool execution falha."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult


class PostToolFailureHandler:
    """Handler para hooks PostToolUseFailure."""

    @staticmethod
    async def execute(
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
        error: str,
        session_id: str,
        *,
        cwd: str | None = None,
        is_interrupt: bool = False,
        permission_mode: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        async for result in manager.execute_post_tool_failure(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            error=error,
            session_id=session_id,
            cwd=cwd,
            is_interrupt=is_interrupt,
            permission_mode=permission_mode,
            timeout=timeout,
        ):
            yield result