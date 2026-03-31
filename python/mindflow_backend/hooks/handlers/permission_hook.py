"""Permission Handlers — Request/Denied hooks para permissões."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult


class PermissionRequestHandler:
    """Handler para hooks PermissionRequest."""

    @staticmethod
    async def execute(
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
        description: str,
        session_id: str,
        *,
        permission_suggestions: list[dict[str, Any]] | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        from mindflow_backend.hooks.context import HookContext
        from mindflow_backend.hooks.types import HookEvent

        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.PERMISSION_REQUEST,
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            description=description,
            permission_suggestions=permission_suggestions,
        )
        async for result in manager.execute(
            HookEvent.PERMISSION_REQUEST,
            ctx,
            match_query=tool_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result


class PermissionDeniedHandler:
    """Handler para hooks PermissionDenied."""

    @staticmethod
    async def execute(
        tool_name: str,
      tool_input: dict[str, Any],
      tool_use_id: str,
      session_id: str,
      *,
      timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        from mindflow_backend.hooks.context import HookContext
        from mindflow_backend.hooks.types import HookEvent

        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.PERMISSION_DENIED,
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
        )
        async for result in manager.execute(
            HookEvent.PERMISSION_DENIED,
            ctx,
            match_query=tool_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result