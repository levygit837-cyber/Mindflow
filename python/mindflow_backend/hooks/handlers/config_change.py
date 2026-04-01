"""ConfigChange Handler — Executado quando configuração muda."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class ConfigChangeHandler:
    """Handler para hooks ConfigChange."""

    @staticmethod
    async def execute(
        session_id: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.CONFIG_CHANGE,
            session_id=session_id,
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.CONFIG_CHANGE,
            ctx,
            match_query=config_key,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result