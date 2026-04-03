"""SessionEnd Handler — Executado ao encerrar sessão."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent
from mindflow_backend.plugins.manager import get_plugin_manager

logger = logging.getLogger(__name__)


class SessionEndHandler:
    """Handler para hooks SessionEnd."""

    @staticmethod
    async def execute(
        session_id: str,
        reason: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        plugin_manager = get_plugin_manager()
        ctx = HookContext(
            hook_event_name=HookEvent.SESSION_END,
            session_id=session_id,
            reason=reason,
            cwd=cwd,
        )
        try:
            async for result in manager.execute(
                HookEvent.SESSION_END,
                ctx,
                match_query=reason,
                timeout=timeout,
                session_id=session_id,
            ):
                yield result
        finally:
            await plugin_manager.deactivate_session(session_id)
