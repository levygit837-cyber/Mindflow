"""File Watcher Handlers — FileChanged e CwdChanged."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent

logger = logging.getLogger(__name__)


class FileChangedHandler:
    """Handler para hooks FileChanged."""

    @staticmethod
    async def execute(
        session_id: str,
        file_path: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.FILE_CHANGED,
            session_id=session_id,
            file_path=file_path,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.FILE_CHANGED,
            ctx,
            match_query=file_path,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result


class CwdChangedHandler:
    """Handler para hooks CwdChanged."""

    @staticmethod
    async def execute(
        session_id: str,
        old_cwd: str,
        new_cwd: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        ctx = HookContext(
            hook_event_name=HookEvent.CWD_CHANGED,
            session_id=session_id,
            old_cwd=old_cwd,
            new_cwd=new_cwd,
            cwd=cwd,
        )
        async for result in manager.execute(
            HookEvent.CWD_CHANGED,
            ctx,
            match_query=new_cwd,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result