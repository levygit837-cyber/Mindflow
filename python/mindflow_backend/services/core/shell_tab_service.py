"""In-memory shell tab service.

Shell tabs are session-scoped mutable process records. They do not persist
across restarts; the service is intentionally lightweight and optimized for the
chat/session lifecycle.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.workspace_security import (
    WorkspaceSecurityError,
    resolve_workspace_path,
    resolve_workspace_root,
    sanitize_environment,
    validate_shell_command,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.shell_tabs import (
    ShellTabContract,
    ShellTabSnapshot,
    ShellTabState,
    ShellTabStatusResponse,
)

_logger = get_logger(__name__)


def _get_session_runtime_state_service():
    try:
        from mindflow_backend.services.core import get_session_runtime_state_service

        return get_session_runtime_state_service()
    except Exception as exc:
        _logger.warning("shell_session_runtime_state_service_unavailable", error=str(exc))
        return None


class ShellTabService:
    """Manage session-scoped shell tabs and their mutable process state."""

    def __init__(self, *, max_buffer_chars: int = 32_000) -> None:
        self._tabs: dict[str, dict[str, ShellTabContract]] = defaultdict(dict)
        self._active_processes: dict[tuple[str, str], asyncio.subprocess.Process] = {}
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._max_buffer_chars = max_buffer_chars
        self._service_lock = asyncio.Lock()
        self._runtime_state_service = None

    async def create_tab(
        self,
        session_id: str,
        cwd: str | None = None,
        title: str | None = None,
        workspace_root: str | None = None,
        read_only: bool = False,
        secure_mode: bool = False,
    ) -> ShellTabContract:
        await self._ensure_session_loaded(session_id)
        default_workspace_root, default_cwd = await self._get_session_workspace_defaults(session_id)
        effective_workspace_root = workspace_root or default_workspace_root
        effective_cwd = cwd or default_cwd
        try:
            if effective_workspace_root or secure_mode:
                resolved_workspace = str(resolve_workspace_root(effective_workspace_root))
                resolved_cwd = str(resolve_workspace_path(effective_cwd or resolved_workspace, resolved_workspace))
            else:
                resolved_workspace = str(resolve_workspace_root(effective_workspace_root)) if effective_workspace_root else None
                resolved_cwd = str(Path(effective_cwd or Path.cwd()).resolve())
        except WorkspaceSecurityError as exc:
            raise ValueError(f"cwd must remain inside the configured workspace: {exc}") from exc

        now = self._now()
        tab = ShellTabContract(
            tab_id=f"tab-{uuid.uuid4().hex[:10]}",
            session_id=session_id,
            cwd=resolved_cwd,
            title=title or Path(resolved_cwd).name or "shell-tab",
            workspace_root=resolved_workspace,
            read_only=read_only,
            secure_mode=secure_mode,
            created_at=now,
            updated_at=now,
        )
        async with self._service_lock:
            self._tabs[session_id][tab.tab_id] = tab
            self._locks[(session_id, tab.tab_id)] = asyncio.Lock()
        _logger.info("shell_tab_created", session_id=session_id, tab_id=tab.tab_id, cwd=resolved_cwd)
        await self._persist_session_state(session_id)
        await self._publish_event("shell_tab_created", tab)
        return tab.model_copy(deep=True)

    async def list_tabs(self, session_id: str) -> list[ShellTabContract]:
        await self._ensure_session_loaded(session_id)
        tabs = self._tabs.get(session_id, {})
        return [tab.model_copy(deep=True) for tab in tabs.values()]

    async def get_tab_status(self, session_id: str, tab_id: str) -> ShellTabStatusResponse:
        await self._ensure_session_loaded(session_id)
        tab = self._get_tab(session_id, tab_id)
        return self._to_status(tab)

    async def exec_in_tab(self, session_id: str, tab_id: str, command: str) -> ShellTabContract:
        await self._ensure_session_loaded(session_id)
        key = (session_id, tab_id)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            tab = self._get_tab(session_id, tab_id)
            if tab.state == ShellTabState.TERMINATED:
                raise ValueError(f"Shell tab {tab_id} is terminated")

            if tab.secure_mode:
                validation_error = validate_shell_command(command, "read_only" if tab.read_only else "full")
                if validation_error:
                    now = self._now()
                    tab.state = ShellTabState.FAILED
                    tab.last_command = command
                    tab.last_exit_code = 1
                    tab.started_at = now
                    tab.completed_at = now
                    tab.updated_at = now
                    tab.stderr_buffer = self._append_buffer(tab.stderr_buffer, f"{validation_error}\n")
                    await self._persist_session_state(session_id)
                    await self._publish_event("shell_tab_failed", tab)
                    return tab.model_copy(deep=True)

            process = await asyncio.create_subprocess_shell(
                command,
                cwd=tab.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=sanitize_environment(cwd=tab.cwd) if tab.secure_mode else None,
            )

            now = self._now()
            tab.pid = process.pid
            tab.state = ShellTabState.RUNNING
            tab.last_command = command
            tab.started_at = now
            tab.updated_at = now
            self._active_processes[key] = process

            _logger.info("shell_tab_exec_start", session_id=session_id, tab_id=tab_id, pid=process.pid, command=command)
            await self._publish_event("shell_tab_running", tab)

            stdout_raw, stderr_raw = await process.communicate()
            stdout = stdout_raw.decode("utf-8", errors="replace") if stdout_raw else ""
            stderr = stderr_raw.decode("utf-8", errors="replace") if stderr_raw else ""

            tab.stdout_buffer = self._append_buffer(tab.stdout_buffer, stdout)
            tab.stderr_buffer = self._append_buffer(tab.stderr_buffer, stderr)
            tab.last_exit_code = process.returncode
            tab.updated_at = self._now()
            tab.completed_at = tab.updated_at
            tab.pid = process.pid
            tab.state = ShellTabState.COMPLETED if process.returncode == 0 else ShellTabState.FAILED

            self._active_processes.pop(key, None)
            _logger.info(
                "shell_tab_exec_complete",
                session_id=session_id,
                tab_id=tab_id,
                exit_code=process.returncode,
                state=tab.state,
            )
            await self._persist_session_state(session_id)
            await self._publish_event(
                "shell_tab_completed" if process.returncode == 0 else "shell_tab_failed",
                tab,
            )
            return tab.model_copy(deep=True)

    async def read_tab_buffer(self, session_id: str, tab_id: str) -> ShellTabSnapshot:
        await self._ensure_session_loaded(session_id)
        tab = self._get_tab(session_id, tab_id)
        return ShellTabSnapshot(
            tab_id=tab.tab_id,
            session_id=tab.session_id,
            state=tab.state,
            stdout_buffer=tab.stdout_buffer,
            stderr_buffer=tab.stderr_buffer,
            updated_at=tab.updated_at,
        )

    async def close_tab(self, session_id: str, tab_id: str) -> ShellTabContract:
        await self._ensure_session_loaded(session_id)
        key = (session_id, tab_id)
        tab = self._get_tab(session_id, tab_id)
        process = self._active_processes.pop(key, None)

        if process is not None and process.returncode is None:
            process.terminate()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=2)
            if process.returncode is None:
                process.kill()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(process.wait(), timeout=1)

        now = self._now()
        tab.state = ShellTabState.TERMINATED
        tab.closed_at = now
        tab.updated_at = now
        if process is not None:
            tab.pid = process.pid
            tab.last_exit_code = process.returncode

        _logger.info("shell_tab_closed", session_id=session_id, tab_id=tab_id)
        await self._persist_session_state(session_id)
        await self._publish_event("shell_tab_terminated", tab)
        return tab.model_copy(deep=True)

    async def subscribe(self, session_id: str) -> AsyncGenerator[dict[str, Any], None]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)

        async with self._service_lock:
            self._subscribers[session_id].add(queue)
            snapshot = {
                "type": "snapshot",
                "session_id": session_id,
                "tabs": [
                    tab.model_dump(mode="json")
                    for tab in self._tabs.get(session_id, {}).values()
                ],
            }

        try:
            yield snapshot
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield {
                        "type": "keepalive",
                        "session_id": session_id,
                        "timestamp": self._now().isoformat(),
                    }
                    continue
                yield event
        finally:
            async with self._service_lock:
                subscribers = self._subscribers.get(session_id)
                if subscribers is not None:
                    subscribers.discard(queue)
                    if not subscribers:
                        self._subscribers.pop(session_id, None)

    def _get_tab(self, session_id: str, tab_id: str) -> ShellTabContract:
        session_tabs = self._tabs.get(session_id, {})
        if tab_id not in session_tabs:
            raise ValueError(f"Shell tab not found: {tab_id}")
        return session_tabs[tab_id]

    async def _get_session_workspace_defaults(self, session_id: str) -> tuple[str | None, str | None]:
        service = self._get_session_runtime_state_service()
        if service is None:
            return None, None

        try:
            snapshot = await service.load_session_state(session_id)
        except Exception as exc:
            _logger.warning("shell_workspace_state_load_failed", session_id=session_id, error=str(exc))
            return None, None

        if not isinstance(snapshot, dict):
            return None, None

        workspace_state = snapshot.get("workspace")
        if not isinstance(workspace_state, dict):
            return None, None

        session_workspace = workspace_state.get("session")
        if not isinstance(session_workspace, dict):
            return None, None

        workspace_root = session_workspace.get("workspace_root")
        workspace_path = session_workspace.get("workspace_path")
        return (
            str(workspace_root) if isinstance(workspace_root, str) and workspace_root else None,
            str(workspace_path) if isinstance(workspace_path, str) and workspace_path else None,
        )

    async def _ensure_session_loaded(self, session_id: str) -> None:
        if self._tabs.get(session_id):
            return

        service = self._get_session_runtime_state_service()
        if service is None:
            return

        try:
            snapshot = await service.load_session_state(session_id)
        except Exception as exc:
            _logger.warning("shell_session_state_load_failed", session_id=session_id, error=str(exc))
            return

        if not snapshot:
            return

        shell_state = snapshot.get("shell_tabs")
        if not isinstance(shell_state, dict):
            return

        tabs = shell_state.get("tabs")
        if not isinstance(tabs, dict):
            return

        session_tabs = self._tabs[session_id]
        for tab_id, tab_state in tabs.items():
            tab_payload: Any
            if isinstance(tab_state, dict) and "tab" in tab_state:
                tab_payload = tab_state["tab"]
            else:
                tab_payload = tab_state

            try:
                tab = ShellTabContract.model_validate(tab_payload)
            except Exception as exc:
                _logger.warning(
                    "shell_session_state_restore_failed",
                    session_id=session_id,
                    tab_id=tab_id,
                    error=str(exc),
                )
                continue

            session_tabs[tab_id] = tab
            self._locks.setdefault((session_id, tab_id), asyncio.Lock())

    async def _persist_session_state(self, session_id: str) -> None:
        service = self._get_session_runtime_state_service()
        if service is None:
            return

        session_tabs = self._tabs.get(session_id, {})
        payload = {
            "shell_tabs": {
                "tabs": {
                    tab_id: {
                        "tab": tab.model_dump(mode="json"),
                        "status": self._to_status(tab).model_dump(mode="json"),
                    }
                    for tab_id, tab in session_tabs.items()
                }
            }
        }

        try:
            await service.save_session_state(session_id, payload)
        except Exception as exc:
            _logger.warning("shell_session_state_persist_failed", session_id=session_id, error=str(exc))

    def _get_session_runtime_state_service(self):
        if self._runtime_state_service is not None:
            return self._runtime_state_service

        self._runtime_state_service = _get_session_runtime_state_service()
        return self._runtime_state_service

    def _append_buffer(self, current: str, addition: str) -> str:
        if not addition:
            return current
        combined = f"{current}{addition}"
        if len(combined) <= self._max_buffer_chars:
            return combined
        return combined[-self._max_buffer_chars :]

    async def _publish_event(self, event_type: str, tab: ShellTabContract) -> None:
        event = {
            "type": event_type,
            "session_id": tab.session_id,
            "tab_id": tab.tab_id,
            "tab": self._to_status(tab).model_dump(mode="json"),
        }
        for subscriber in tuple(self._subscribers.get(tab.session_id, ())):
            with contextlib.suppress(asyncio.QueueFull):
                subscriber.put_nowait(event)

    def _to_status(self, tab: ShellTabContract) -> ShellTabStatusResponse:
        return ShellTabStatusResponse(
            tab_id=tab.tab_id,
            session_id=tab.session_id,
            cwd=tab.cwd,
            title=tab.title,
            pid=tab.pid,
            state=tab.state,
            last_command=tab.last_command,
            last_exit_code=tab.last_exit_code,
            stdout_preview=tab.stdout_buffer[-400:],
            stderr_preview=tab.stderr_buffer[-400:],
            updated_at=tab.updated_at,
        )

    def _now(self) -> datetime:
        return datetime.now(UTC)
