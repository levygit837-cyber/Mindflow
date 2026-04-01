"""Task Lifecycle Handlers — TaskCreated e TaskCompleted."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class TaskCreatedHandler:
    """Handler para hooks TaskCreated."""

    @staticmethod
    async def execute(
        session_id: str,
        task_id: str,
        task_name: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.TASK_CREATED,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.TASK_CREATED,
            ctx,
            match_query=task_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result


class TaskCompletedHandler:
    """Handler para hooks TaskCompleted."""

    @staticmethod
    async def execute(
        session_id: str,
        task_id: str,
        task_name: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.TASK_COMPLETED,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.TASK_COMPLETED,
            ctx,
            match_query=task_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result