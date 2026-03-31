"""Stop Handler — Executado ao fim de sessão/missão."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult


class StopHandler:
    """Handler para hooks Stop/AgentStop."""

    @staticmethod
    async def execute(
        session_id: str,
        *,
        cwd: str | None = None,
        is_subagent: bool = False,
        agent_id: str | None = None,
        agent_type: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        async for result in manager.execute_stop(
            session_id=session_id,
            cwd=cwd,
            is_subagent=is_subagent,
            agent_id=agent_id,
            agent_type=agent_type,
            timeout=timeout,
        ):
            yield result