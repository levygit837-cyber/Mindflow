"""Notification Handler — Executado para notificações."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class NotificationHandler:
    """Handler para hooks Notification."""

    @staticmethod
    async def execute(
        session_id: str,
        notification_type: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.NOTIFICATION,
            session_id=session_id,
            notification_type=notification_type,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.NOTIFICATION,
            ctx,
            match_query=notification_type,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result