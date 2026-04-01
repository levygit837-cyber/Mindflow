"""StopFailure Handler — Executado quando Stop falha."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class StopFailureHandler:
    """Handler para hooks StopFailure."""

    @staticmethod
    async def execute(
        session_id: str,
        stop_error: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.STOP_FAILURE,
            session_id=session_id,
            stop_error=stop_error,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.STOP_FAILURE,
            ctx,
            match_query=stop_error,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result