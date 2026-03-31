"""SessionStart Handler — Executado ao iniciar sessão."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult


class SessionStartHandler:
    """Handler para hooks SessionStart."""

    @staticmethod
    async def execute(
        session_id: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        async for result in manager.execute_session_start(
            session_id=session_id,
            cwd=cwd,
            timeout=timeout,
        ):
            yield result