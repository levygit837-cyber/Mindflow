"""Setup Handler — Executado durante setup do sistema."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class SetupHandler:
    """Handler para hooks Setup."""

    @staticmethod
    async def execute(
        session_id: str,
        setup_trigger: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.SETUP,
            session_id=session_id,
            setup_trigger=setup_trigger,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.SETUP,
            ctx,
            match_query=setup_trigger,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result