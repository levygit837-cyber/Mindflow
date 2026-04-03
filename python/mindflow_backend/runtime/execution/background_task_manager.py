"""Persisted background task management for tool subprocesses."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.orchestration import get_execution_task_service
from mindflow_backend.services.orchestration.execution_task_service import ExecutionTaskService

_logger = get_logger(__name__)


@dataclass(slots=True)
class BackgroundTaskHandle:
    """Public handle returned when a background task is spawned."""

    background_task_id: str
    pid: int
    command: str
    stdout_path: Path
    stderr_path: Path
    status: str
    execution_task_id: str | None = None


@dataclass
class _BackgroundTaskRecord:
    """Internal mutable record for one background task."""

    handle: BackgroundTaskHandle
    process: asyncio.subprocess.Process
    stdout_stream: BinaryIO
    stderr_stream: BinaryIO
    monitor_task: asyncio.Task[None] | None = None
    session_id: str | None = None
    task_id: str | None = None
    tool_call_id: str | None = None
    status: str = "running"
    exit_code: int | None = None
    error: str | None = None


class BackgroundTaskManager:
    """Manage long-running subprocesses with persisted runtime state."""

    def __init__(
        self,
        *,
        execution_task_service: ExecutionTaskService | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self._execution_task_service = execution_task_service or get_execution_task_service()
        self._output_dir = Path(output_dir) if output_dir else (
            Path(tempfile.gettempdir()) / "mindflow_background_tasks"
        )
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, _BackgroundTaskRecord] = {}
        self._lock = asyncio.Lock()

    async def spawn(
        self,
        *,
        command: str,
        cwd: str | None,
        env: dict[str, str] | None,
        description: str,
        session_id: str | None = None,
        task_id: str | None = None,
        tool_call_id: str | None = None,
    ) -> BackgroundTaskHandle:
        """Start a subprocess in the background and persist its metadata."""
        background_task_id = f"bg-{uuid.uuid4().hex}"
        normalized_command = self._normalize_command(command)
        stdout_path = self._output_dir / f"{background_task_id}.stdout.log"
        stderr_path = self._output_dir / f"{background_task_id}.stderr.log"
        stdout_stream = stdout_path.open("wb")
        stderr_stream = stderr_path.open("wb")
        environment = os.environ.copy()
        if env:
            environment.update(env)

        try:
            process = await asyncio.create_subprocess_shell(
                normalized_command,
                cwd=cwd,
                env=environment,
                stdout=stdout_stream,
                stderr=stderr_stream,
            )
        except Exception:
            stdout_stream.close()
            stderr_stream.close()
            raise

        execution_task_id: str | None = None
        if session_id and task_id:
            execution = await self._execution_task_service.start_execution(
                session_id=session_id,
                task_id=task_id,
                description=description,
                execution_type="tool_call",
                execution_key=tool_call_id or background_task_id,
                metadata={
                    "background_task_id": background_task_id,
                    "tool_call_id": tool_call_id,
                    "pid": process.pid,
                    "command": normalized_command,
                },
            )
            execution_task_id = execution.execution_task_id

        handle = BackgroundTaskHandle(
            background_task_id=background_task_id,
            pid=process.pid,
            command=normalized_command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            status="running",
            execution_task_id=execution_task_id,
        )
        record = _BackgroundTaskRecord(
            handle=handle,
            process=process,
            stdout_stream=stdout_stream,
            stderr_stream=stderr_stream,
            session_id=session_id,
            task_id=task_id,
            tool_call_id=tool_call_id,
        )
        record.monitor_task = asyncio.create_task(
            self._monitor(record),
            name=f"background-task-{background_task_id}",
        )

        async with self._lock:
            self._records[background_task_id] = record

        return handle

    @staticmethod
    def _normalize_command(command: str) -> str:
        """Adjust commands for environments where `python` is unavailable."""
        stripped = command.lstrip()
        if stripped.startswith("python ") and shutil.which("python") is None:
            python3_path = shutil.which("python3")
            if python3_path:
                prefix_len = len(command) - len(stripped)
                return f"{command[:prefix_len]}{python3_path}{stripped[len('python'):]}"
        return command

    async def get_status(self, background_task_id: str) -> dict[str, Any]:
        """Return current status for a background task."""
        record = self._records.get(background_task_id)
        if record is None:
            return {
                "success": False,
                "error": f"Background task not found: {background_task_id}",
                "error_code": "BACKGROUND_TASK_NOT_FOUND",
            }

        if record.status == "running" and record.process.returncode is not None:
            monitor_task = record.monitor_task
            if monitor_task is not None and not monitor_task.done():
                await monitor_task

        response = {
            "success": True,
            "background_task_id": background_task_id,
            "process_id": background_task_id,
            "pid": record.handle.pid,
            "status": record.status,
            "exit_code": record.exit_code,
            "stdout_path": str(record.handle.stdout_path),
            "stderr_path": str(record.handle.stderr_path),
        }

        if record.status != "running":
            response["stdout"] = self._read_file(record.handle.stdout_path)
            response["stderr"] = self._read_file(record.handle.stderr_path)
            if record.error:
                response["error"] = record.error

        return response

    async def kill(self, background_task_id: str) -> dict[str, Any]:
        """Kill a running background task."""
        record = self._records.get(background_task_id)
        if record is None:
            return {
                "success": False,
                "error": f"Background task not found: {background_task_id}",
                "error_code": "BACKGROUND_TASK_NOT_FOUND",
            }

        if record.status != "running":
            return {
                "success": True,
                "background_task_id": background_task_id,
                "process_id": background_task_id,
                "pid": record.handle.pid,
                "status": record.status,
            }

        record.process.kill()
        await record.process.wait()
        record.status = "killed"
        record.handle.status = "killed"
        record.exit_code = record.process.returncode
        await self._close_streams(record)

        if record.monitor_task is not None and not record.monitor_task.done():
            record.monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await record.monitor_task

        await self._sync_runtime_state(record)

        return {
            "success": True,
            "background_task_id": background_task_id,
            "process_id": background_task_id,
            "pid": record.handle.pid,
            "status": record.status,
        }

    async def _monitor(self, record: _BackgroundTaskRecord) -> None:
        """Watch a subprocess and persist its terminal state."""
        try:
            return_code = await record.process.wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            record.status = "failed"
            record.handle.status = "failed"
            record.error = str(exc)
            _logger.warning(
                "background_task_monitor_failed",
                background_task_id=record.handle.background_task_id,
                error=str(exc),
            )
        else:
            if record.status == "killed":
                return
            record.exit_code = return_code
            if return_code == 0:
                record.status = "completed"
                record.handle.status = "completed"
            else:
                record.status = "failed"
                record.handle.status = "failed"
                record.error = f"Process exited with code {return_code}"
        finally:
            await self._close_streams(record)
            await self._sync_runtime_state(record)

    async def _sync_runtime_state(self, record: _BackgroundTaskRecord) -> None:
        """Persist current task state into ExecutionTaskService."""
        if not record.session_id or not record.task_id or not record.handle.execution_task_id:
            return

        if record.status == "completed":
            await self._execution_task_service.complete_execution(
                session_id=record.session_id,
                execution_task_id=record.handle.execution_task_id,
                output_ref=str(record.handle.stdout_path),
                metadata={
                    "background_task_id": record.handle.background_task_id,
                    "stderr_path": str(record.handle.stderr_path),
                    "pid": record.handle.pid,
                },
            )
            return

        if record.status == "killed":
            await self._execution_task_service.kill_execution(
                session_id=record.session_id,
                execution_task_id=record.handle.execution_task_id,
                reason=record.error or "Background process killed",
                metadata={
                    "background_task_id": record.handle.background_task_id,
                    "stdout_path": str(record.handle.stdout_path),
                    "stderr_path": str(record.handle.stderr_path),
                    "pid": record.handle.pid,
                },
            )
            return

        if record.status == "failed":
            await self._execution_task_service.fail_execution(
                session_id=record.session_id,
                execution_task_id=record.handle.execution_task_id,
                error=record.error or "Background process failed",
                metadata={
                    "background_task_id": record.handle.background_task_id,
                    "stdout_path": str(record.handle.stdout_path),
                    "stderr_path": str(record.handle.stderr_path),
                    "pid": record.handle.pid,
                },
            )

    async def _close_streams(self, record: _BackgroundTaskRecord) -> None:
        """Close log streams for a record."""
        for stream in (record.stdout_stream, record.stderr_stream):
            with contextlib.suppress(Exception):
                stream.flush()
            with contextlib.suppress(Exception):
                stream.close()

    @staticmethod
    def _read_file(path: Path) -> str:
        """Read a text file defensively."""
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
