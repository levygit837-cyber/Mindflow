"""Runtime execution task service for orchestrated work."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.execution_tasks import (
    ExecutionTaskContract,
    ExecutionTaskControl,
    ExecutionTaskStatus,
    ExecutionTaskType,
)

_logger = get_logger(__name__)

_ACTIVE_EXECUTION_STATUSES = {
    ExecutionTaskStatus.PENDING,
    ExecutionTaskStatus.RUNNING,
}
_TERMINAL_EXECUTION_STATUSES = {
    ExecutionTaskStatus.COMPLETED,
    ExecutionTaskStatus.FAILED,
    ExecutionTaskStatus.KILLED,
}


def _get_session_runtime_state_service():
    try:
        from mindflow_backend.services.core import get_session_runtime_state_service

        return get_session_runtime_state_service()
    except Exception as exc:
        _logger.warning("execution_task_session_runtime_state_service_unavailable", error=str(exc))
        return None


class ExecutionTaskService:
    """Manage runtime execution tasks for a task list."""

    def __init__(self) -> None:
        self._executions: dict[str, dict[str, ExecutionTaskContract]] = defaultdict(dict)
        self._task_index: dict[str, str] = {}
        self._task_control: dict[str, dict[str, ExecutionTaskControl]] = defaultdict(dict)
        self._loaded_sessions: set[str] = set()
        self._lock = asyncio.Lock()

    async def start_execution(
        self,
        *,
        session_id: str,
        task_id: str,
        description: str,
        execution_type: str = "workflow_step",
        item_id: str | None = None,
        execution_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionTaskContract:
        await self._ensure_session_loaded(session_id)
        async with self._lock:
            now = self._now()
            execution_type_enum = ExecutionTaskType(execution_type)
            normalized_key = execution_key or (f"item:{item_id}" if item_id else execution_type_enum.value)
            attempt = self._next_attempt(session_id, task_id, normalized_key)
            execution_task_id = f"{task_id}:{normalized_key}:attempt-{attempt}"

            execution = ExecutionTaskContract(
                execution_task_id=execution_task_id,
                session_id=session_id,
                task_id=task_id,
                item_id=item_id,
                execution_key=normalized_key,
                type=execution_type_enum,
                status=ExecutionTaskStatus.RUNNING,
                description=description,
                attempt=attempt,
                metadata=dict(metadata or {}),
                created_at=now,
                updated_at=now,
                started_at=now,
            )
            self._executions[session_id][execution_task_id] = execution
            self._task_index[task_id] = session_id

        await self._persist_session_state(session_id)
        return execution.model_copy(deep=True)

    async def append_output(
        self,
        *,
        session_id: str,
        execution_task_id: str,
        chunk: str,
    ) -> ExecutionTaskContract:
        await self._ensure_session_loaded(session_id)
        if not chunk:
            return (await self.get_execution(session_id=session_id, execution_task_id=execution_task_id))

        async with self._lock:
            execution = self._get_required_execution(session_id, execution_task_id)
            if execution.status in _TERMINAL_EXECUTION_STATUSES:
                return execution.model_copy(deep=True)
            execution.output.append(chunk)
            execution.updated_at = self._now()

        await self._persist_session_state(session_id)
        return execution.model_copy(deep=True)

    async def get_execution(
        self,
        *,
        session_id: str,
        execution_task_id: str,
    ) -> ExecutionTaskContract:
        await self._ensure_session_loaded(session_id)
        execution = self._get_required_execution(session_id, execution_task_id)
        return execution.model_copy(deep=True)

    async def complete_execution(
        self,
        *,
        session_id: str,
        execution_task_id: str,
        output_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionTaskContract:
        return await self._transition_execution(
            session_id=session_id,
            execution_task_id=execution_task_id,
            status=ExecutionTaskStatus.COMPLETED,
            output_ref=output_ref,
            metadata=metadata,
        )

    async def fail_execution(
        self,
        *,
        session_id: str,
        execution_task_id: str,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionTaskContract:
        return await self._transition_execution(
            session_id=session_id,
            execution_task_id=execution_task_id,
            status=ExecutionTaskStatus.FAILED,
            error=error,
            metadata=metadata,
        )

    async def kill_execution(
        self,
        *,
        session_id: str,
        execution_task_id: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionTaskContract:
        return await self._transition_execution(
            session_id=session_id,
            execution_task_id=execution_task_id,
            status=ExecutionTaskStatus.KILLED,
            error=reason,
            metadata=metadata,
        )

    async def list_task_executions(
        self,
        *,
        session_id: str,
        task_id: str,
    ) -> list[ExecutionTaskContract]:
        await self._ensure_session_loaded(session_id)
        executions = [
            execution.model_copy(deep=True)
            for execution in self._executions.get(session_id, {}).values()
            if execution.task_id == task_id
        ]
        executions.sort(key=self._sort_key, reverse=True)
        return executions

    async def list_task_executions_by_task_id(self, task_id: str) -> list[ExecutionTaskContract]:
        session_id = await self._resolve_session_id(task_id)
        if session_id is None:
            raise ValueError(f"Execution tasks not found for task={task_id}")
        return await self.list_task_executions(session_id=session_id, task_id=task_id)

    async def get_task_overview(self, task_id: str) -> dict[str, Any]:
        session_id = await self._resolve_session_id(task_id)
        if session_id is None:
            return {
                "task_id": task_id,
                "status": "not_started",
                "cancel_requested": False,
                "counts": {},
                "latest_execution_id": None,
                "active_execution_ids": [],
            }

        executions = await self.list_task_executions(session_id=session_id, task_id=task_id)
        control = self._task_control.get(session_id, {}).get(task_id, ExecutionTaskControl())
        counter = Counter(execution.status.value for execution in executions)
        active_execution_ids = [
            execution.execution_task_id
            for execution in executions
            if execution.status in _ACTIVE_EXECUTION_STATUSES
        ]

        if control.cancel_requested:
            status = "cancelling"
        elif counter.get(ExecutionTaskStatus.RUNNING.value):
            status = ExecutionTaskStatus.RUNNING.value
        elif counter.get(ExecutionTaskStatus.PENDING.value):
            status = ExecutionTaskStatus.PENDING.value
        elif executions:
            status = executions[0].status.value
        else:
            status = "not_started"

        return {
            "task_id": task_id,
            "status": status,
            "cancel_requested": control.cancel_requested,
            "counts": dict(counter),
            "latest_execution_id": executions[0].execution_task_id if executions else None,
            "active_execution_ids": active_execution_ids,
        }

    async def request_task_cancellation(
        self,
        *,
        session_id: str,
        task_id: str,
        reason: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        await self._ensure_session_loaded(session_id)
        async with self._lock:
            now = self._now()
            control = self._task_control[session_id].get(task_id, ExecutionTaskControl())
            control.cancel_requested = True
            control.cancel_requested_at = now
            control.cancel_reason = reason
            control.force = force
            self._task_control[session_id][task_id] = control
            self._task_index[task_id] = session_id

            killed_executions = 0
            for execution in self._executions.get(session_id, {}).values():
                if execution.task_id != task_id:
                    continue
                if execution.status not in _ACTIVE_EXECUTION_STATUSES:
                    continue
                execution.status = ExecutionTaskStatus.KILLED
                execution.error = reason or execution.error
                execution.updated_at = now
                execution.ended_at = now
                killed_executions += 1

        await self._persist_session_state(session_id)
        return {
            "task_id": task_id,
            "cancel_requested": True,
            "reason": reason,
            "force": force,
            "killed_executions": killed_executions,
        }

    async def clear_task_cancellation(self, *, session_id: str, task_id: str) -> dict[str, Any]:
        await self._ensure_session_loaded(session_id)
        async with self._lock:
            control = self._task_control[session_id].get(task_id, ExecutionTaskControl())
            self._task_control[session_id][task_id] = ExecutionTaskControl()
            self._task_index[task_id] = session_id

        await self._persist_session_state(session_id)
        return {
            "task_id": task_id,
            "cancel_requested": False,
            "previous_cancel_requested": control.cancel_requested,
        }

    async def is_cancellation_requested(self, *, session_id: str, task_id: str) -> bool:
        await self._ensure_session_loaded(session_id)
        return self._task_control.get(session_id, {}).get(task_id, ExecutionTaskControl()).cancel_requested

    def _next_attempt(self, session_id: str, task_id: str, execution_key: str) -> int:
        attempts = [
            execution.attempt
            for execution in self._executions.get(session_id, {}).values()
            if execution.task_id == task_id and execution.execution_key == execution_key
        ]
        return (max(attempts) if attempts else 0) + 1

    def _get_required_execution(self, session_id: str, execution_task_id: str) -> ExecutionTaskContract:
        execution = self._executions.get(session_id, {}).get(execution_task_id)
        if execution is None:
            raise ValueError(f"Execution task not found for session={session_id} execution={execution_task_id}")
        return execution

    async def _transition_execution(
        self,
        *,
        session_id: str,
        execution_task_id: str,
        status: ExecutionTaskStatus,
        output_ref: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionTaskContract:
        await self._ensure_session_loaded(session_id)
        async with self._lock:
            execution = self._get_required_execution(session_id, execution_task_id)
            if execution.status == ExecutionTaskStatus.KILLED and status != ExecutionTaskStatus.KILLED:
                return execution.model_copy(deep=True)

            now = self._now()
            execution.status = status
            if output_ref is not None:
                execution.output_ref = output_ref
            if error is not None:
                execution.error = error
            if metadata:
                execution.metadata.update(metadata)
            execution.updated_at = now
            if status in _TERMINAL_EXECUTION_STATUSES:
                execution.ended_at = now

        await self._persist_session_state(session_id)
        return execution.model_copy(deep=True)

    async def _ensure_session_loaded(self, session_id: str) -> None:
        if session_id in self._loaded_sessions:
            return

        service = _get_session_runtime_state_service()
        self._loaded_sessions.add(session_id)
        if service is None:
            return

        try:
            snapshot = await service.load_session_state(session_id)
        except Exception as exc:
            _logger.warning("execution_task_state_load_failed", session_id=session_id, error=str(exc))
            return

        if not snapshot:
            return

        execution_state = snapshot.get("execution_tasks")
        if not isinstance(execution_state, dict):
            return

        tasks = execution_state.get("tasks")
        if not isinstance(tasks, dict):
            return

        session_executions = self._executions[session_id]
        for task_id, task_state in tasks.items():
            if not isinstance(task_state, dict):
                continue
            self._task_index[task_id] = session_id
            control_payload = task_state.get("control") or {}
            try:
                self._task_control[session_id][task_id] = ExecutionTaskControl.model_validate(control_payload)
            except Exception as exc:
                _logger.warning(
                    "execution_task_control_restore_failed",
                    session_id=session_id,
                    task_id=task_id,
                    error=str(exc),
                )
                self._task_control[session_id][task_id] = ExecutionTaskControl()

            executions_payload = task_state.get("executions")
            if not isinstance(executions_payload, dict):
                continue
            for execution_task_id, execution_payload in executions_payload.items():
                try:
                    execution = ExecutionTaskContract.model_validate(execution_payload)
                except Exception as exc:
                    _logger.warning(
                        "execution_task_restore_failed",
                        session_id=session_id,
                        task_id=task_id,
                        execution_task_id=execution_task_id,
                        error=str(exc),
                    )
                    continue
                session_executions[execution_task_id] = execution
                self._task_index[task_id] = session_id

    async def _persist_session_state(self, session_id: str) -> None:
        service = _get_session_runtime_state_service()
        if service is None:
            return

        executions_by_task: dict[str, dict[str, Any]] = defaultdict(dict)
        for execution_task_id, execution in self._executions.get(session_id, {}).items():
            executions_by_task[execution.task_id][execution_task_id] = execution.model_dump(mode="json")

        task_ids = set(executions_by_task.keys()) | set(self._task_control.get(session_id, {}).keys())
        payload = {
            "execution_tasks": {
                "tasks": {
                    task_id: {
                        "executions": executions_by_task.get(task_id, {}),
                        "control": self._task_control.get(session_id, {}).get(
                            task_id,
                            ExecutionTaskControl(),
                        ).model_dump(mode="json"),
                    }
                    for task_id in task_ids
                }
            }
        }

        try:
            await service.save_session_state(session_id, payload)
        except Exception as exc:
            _logger.warning("execution_task_state_persist_failed", session_id=session_id, error=str(exc))

    def _sort_key(self, execution: ExecutionTaskContract) -> tuple[datetime, datetime]:
        return (execution.updated_at, execution.created_at)

    async def _resolve_session_id(self, task_id: str) -> str | None:
        session_id = self._task_index.get(task_id)
        if session_id is not None:
            return session_id

        service = _get_session_runtime_state_service()
        if service is None or not hasattr(service, "list_session_states"):
            return None

        try:
            session_states = await service.list_session_states()
        except Exception as exc:
            _logger.warning("execution_task_state_scan_failed", task_id=task_id, error=str(exc))
            return None

        for session_state in session_states:
            candidate_session_id = session_state.get("session_id")
            execution_state = session_state.get("execution_tasks")
            if not candidate_session_id or not isinstance(execution_state, dict):
                continue
            tasks = execution_state.get("tasks")
            if not isinstance(tasks, dict) or task_id not in tasks:
                continue
            await self._ensure_session_loaded(str(candidate_session_id))
            return self._task_index.get(task_id)

        return None

    def _now(self) -> datetime:
        return datetime.now(UTC)
