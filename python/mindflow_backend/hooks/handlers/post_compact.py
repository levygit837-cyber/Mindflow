"""PostCompact Handler — Executado após compactação."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class PostCompactHandler:
    """Handler para hooks PostCompact."""

    @staticmethod
    async def execute(
        session_id: str,
        trigger: str,
        summary: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.POST_COMPACT,
            session_id=session_id,
            trigger=trigger,
            summary=summary,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.POST_COMPACT,
            ctx,
            match_query=trigger,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result