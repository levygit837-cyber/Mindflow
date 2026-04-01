"""PreCompact Handler — Executado antes de compactação."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class PreCompactHandler:
    """Handler para hooks PreCompact."""

    @staticmethod
    async def execute(
        session_id: str,
        trigger: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.PRE_COMPACT,
            session_id=session_id,
            trigger=trigger,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.PRE_COMPACT,
            ctx,
            match_query=trigger,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result