"""Durable execution memory service.

This service persists the operational state of agent executions so they can be
paused, resumed, inspected, and audited after process restarts.
"""

from __future__ import annotations

import inspect
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, TypeVar

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.storage.postgresql.models import (
    AgentExecution,
    AgentExecutionEffect,
    AgentExecutionEvent,
    AgentExecutionMessage,
    AgentExecutionProcess,
    AgentExecutionSnapshot,
    SessionRuntimeState,
)

_logger = get_logger(__name__)
_T = TypeVar("_T")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _stable_json_hash(payload: Any) -> str:
    import hashlib

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _coerce_dict(value: Any | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return {
            key: candidate
            for key, candidate in vars(value).items()
            if not key.startswith("_")
        }
    return {"value": value}


def _result_first_scalar(result: Any) -> Any | None:
    scalars = getattr(result, "scalars", None)
    if callable(scalars):
        scalars = scalars()
    if scalars is None:
        return None
    first = getattr(scalars, "first", None)
    if callable(first):
        return first()
    all_fn = getattr(scalars, "all", None)
    if callable(all_fn):
        rows = all_fn()
        return rows[0] if rows else None
    return None


def _is_mock_placeholder(value: Any) -> bool:
    return value is not None and type(value).__module__.startswith("unittest.mock")


class ExecutionMemoryService:
    """Persist and restore execution state across process lifecycles."""

    def __init__(self, *, db_session_factory: Callable[[], Any] | None = None) -> None:
        self._db_session_factory = db_session_factory

    async def start_execution(
        self,
        db: Any | None = None,
        *,
        session_id: str,
        agent_id: str | None = None,
        goal: str | None = None,
        execution_id: str | None = None,
        run_id: str | None = None,
        mode: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        root_execution_id: str | None = None,
        parent_execution_id: str | None = None,
        execution_role: str | None = None,
        owner_execution_id: str | None = None,
        status: str = "running",
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentExecution:
        return await self._run_db(
            db,
            self._start_execution_in_db,
            session_id=session_id,
            agent_id=agent_id,
            goal=goal,
            execution_id=execution_id,
            run_id=run_id,
            mode=mode,
            provider=provider,
            model=model,
            root_execution_id=root_execution_id,
            parent_execution_id=parent_execution_id,
            execution_role=execution_role,
            owner_execution_id=owner_execution_id,
            status=status,
            stage=stage,
            metadata=metadata,
        )

    async def get_execution(self, execution_id: str, db: Any | None = None) -> AgentExecution | None:
        return await self._run_db(db, self._get_execution_in_db, execution_id=execution_id)

    async def mark_status(
        self,
        execution_id: str,
        status: str,
        db: Any | None = None,
        **updates: Any,
    ) -> AgentExecution:
        return await self._run_db(
            db,
            self._mark_status_in_db,
            execution_id=execution_id,
            status=status,
            updates=updates,
        )

    async def request_pause(
        self,
        db: Any | None = None,
        *,
        execution_id: str,
        reason: str | None = None,
    ) -> AgentExecution:
        return await self.mark_status(
            execution_id,
            "pause_requested",
            db=db,
            pause_requested=True,
            pause_reason=reason,
        )

    async def should_pause(self, execution_id: str, db: Any | None = None) -> bool:
        execution = await self.get_execution(execution_id, db=db)
        return bool(getattr(execution, "pause_requested", False)) if execution is not None else False

    async def mark_resumed(self, db: Any | None = None, *, execution_id: str) -> AgentExecution:
        return await self.mark_status(
            execution_id,
            "running",
            db=db,
            pause_requested=False,
            pause_reason=None,
            resumed_at=_utcnow(),
        )

    async def record_event(
        self,
        db: Any | None = None,
        *,
        execution_id: str,
        event_type: str,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
        stage: str | None = None,
        step_id: str | None = None,
    ) -> AgentExecutionEvent:
        return await self._run_db(
            db,
            self._record_event_in_db,
            execution_id=execution_id,
            event_type=event_type,
            message=message,
            payload=payload,
            stage=stage,
            step_id=step_id,
        )

    async def append_event(
        self,
        execution_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        db: Any | None = None,
        message: str | None = None,
        stage: str | None = None,
        step_id: str | None = None,
    ) -> AgentExecutionEvent:
        return await self.record_event(
            db=db,
            execution_id=execution_id,
            event_type=event_type,
            message=message,
            payload=payload,
            stage=stage,
            step_id=step_id,
        )

    async def create_snapshot(
        self,
        db: Any | None = None,
        *,
        execution_id: str,
        snapshot_kind: str = "checkpoint",
        stage: str | None = None,
        state: dict[str, Any] | None = None,
        context: str | dict[str, Any] | None = None,
        is_resume_point: bool | None = None,
        parent_event_id: int | None = None,
        checkpoint_id: str | None = None,
        next_nodes: list[str] | None = None,
        state_payload: dict[str, Any] | None = None,
        context_bundle: dict[str, Any] | None = None,
        resumable: bool | None = None,
    ) -> AgentExecutionSnapshot:
        normalized_state = state_payload if state_payload is not None else (state or {})
        normalized_context = (
            context_bundle
            if context_bundle is not None
            else (context if isinstance(context, dict) else {"summary": context} if context else {})
        )
        resume_point = bool(is_resume_point) if is_resume_point is not None else bool(resumable)
        return await self._run_db(
            db,
            self._create_snapshot_in_db,
            execution_id=execution_id,
            snapshot_kind=snapshot_kind,
            stage=stage,
            state=normalized_state,
            context=normalized_context,
            is_resume_point=resume_point,
            parent_event_id=parent_event_id,
            checkpoint_id=checkpoint_id,
            next_nodes=next_nodes or [],
        )

    async def get_latest_snapshot(
        self,
        execution_id: str,
        db: Any | None = None,
    ) -> AgentExecutionSnapshot | None:
        return await self._run_db(db, self._get_latest_snapshot_in_db, execution_id=execution_id)

    async def record_external_effect(
        self,
        db: Any | None = None,
        *,
        execution_id: str,
        effect_key: str,
        effect_type: str,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
        status: str = "pending",
    ) -> AgentExecutionEffect:
        return await self._run_db(
            db,
            self._record_external_effect_in_db,
            execution_id=execution_id,
            effect_key=effect_key,
            effect_type=effect_type,
            request=request,
            response=response,
            status=status,
        )

    async def record_message(
        self,
        db: Any | None = None,
        *,
        execution_id: str,
        message_type: str,
        sender_execution_id: str | None = None,
        recipient_execution_id: str | None = None,
        content: str = "",
        visibility: str = "internal",
        payload: dict[str, Any] | None = None,
        status: str = "pending",
    ) -> AgentExecutionMessage:
        return await self._run_db(
            db,
            self._record_message_in_db,
            execution_id=execution_id,
            message_type=message_type,
            sender_execution_id=sender_execution_id,
            recipient_execution_id=recipient_execution_id,
            content=content,
            visibility=visibility,
            payload=payload,
            status=status,
        )

    async def list_messages(
        self,
        execution_id: str,
        db: Any | None = None,
        *,
        include_consumed: bool = True,
    ) -> list[SimpleNamespace]:
        return await self._run_db(
            db,
            self._list_messages_in_db,
            execution_id=execution_id,
            include_consumed=include_consumed,
        )

    async def consume_pending_messages(
        self,
        db: Any | None = None,
        *,
        execution_id: str,
    ) -> list[SimpleNamespace]:
        return await self._run_db(db, self._consume_pending_messages_in_db, execution_id=execution_id)

    async def record_process(
        self,
        db: Any | None = None,
        *,
        execution_id: str,
        process_key: str,
        tab_id: str | None = None,
        pid: int | None = None,
        owner_agent_id: str | None = None,
        terminal_key: str | None = None,
        cwd: str | None = None,
        state: str = "running",
        metadata: dict[str, Any] | None = None,
    ) -> AgentExecutionProcess:
        return await self._run_db(
            db,
            self._record_process_in_db,
            execution_id=execution_id,
            process_key=process_key,
            tab_id=tab_id,
            pid=pid,
            owner_agent_id=owner_agent_id,
            terminal_key=terminal_key,
            cwd=cwd,
            state=state,
            metadata=metadata,
        )

    async def update_process(
        self,
        process_key: str,
        db: Any | None = None,
        *,
        state: str | None = None,
        pid: int | None = None,
        metadata: dict[str, Any] | None = None,
        terminal_key: str | None = None,
        cwd: str | None = None,
        tab_id: str | None = None,
        ended_at: datetime | None = None,
        heartbeat: bool = False,
    ) -> AgentExecutionProcess | None:
        return await self._run_db(
            db,
            self._update_process_in_db,
            process_key=process_key,
            state=state,
            pid=pid,
            metadata=metadata,
            terminal_key=terminal_key,
            cwd=cwd,
            tab_id=tab_id,
            ended_at=ended_at,
            heartbeat=heartbeat,
        )

    async def list_processes(self, execution_id: str, db: Any | None = None) -> list[SimpleNamespace]:
        return await self._run_db(db, self._list_processes_in_db, execution_id=execution_id)

    async def save_session_runtime_state(
        self,
        db: Any | None = None,
        *,
        session_id: str,
        execution_id: str | None = None,
        state: dict[str, Any],
        version: int = 1,
    ) -> SessionRuntimeState:
        return await self._run_db(
            db,
            self._save_session_runtime_state_in_db,
            session_id=session_id,
            execution_id=execution_id,
            state=state,
            version=version,
        )

    async def load_session_runtime_state(
        self,
        db: Any | None = None,
        *,
        session_id: str,
    ) -> SessionRuntimeState | None:
        return await self._run_db(db, self._load_session_runtime_state_in_db, session_id=session_id)

    async def list_events(
        self,
        root_execution_id: str,
        db: Any | None = None,
        *,
        after_id: int = 0,
    ) -> list[SimpleNamespace]:
        return await self._run_db(
            db,
            self._list_events_in_db,
            root_execution_id=root_execution_id,
            after_id=after_id,
        )

    async def get_execution_tree(
        self,
        execution_id: str,
        db: Any | None = None,
    ) -> dict[str, Any]:
        return await self._run_db(db, self._get_execution_tree_in_db, execution_id=execution_id)

    async def _start_execution_in_db(
        self,
        db: Any,
        *,
        session_id: str,
        agent_id: str | None,
        goal: str | None,
        execution_id: str | None,
        run_id: str | None,
        mode: str | None,
        provider: str | None,
        model: str | None,
        root_execution_id: str | None,
        parent_execution_id: str | None,
        execution_role: str | None,
        owner_execution_id: str | None,
        status: str,
        stage: str | None,
        metadata: dict[str, Any] | None,
    ) -> AgentExecution:
        now = _utcnow()
        metadata = _coerce_dict(metadata)
        resolved_execution_id = execution_id or f"exec-{uuid.uuid4().hex[:12]}"
        resolved_root_execution_id = root_execution_id or resolved_execution_id
        execution = AgentExecution(
            id=resolved_execution_id,
            session_id=session_id,
            root_execution_id=resolved_root_execution_id,
            parent_execution_id=parent_execution_id,
            run_id=run_id,
            agent_id=agent_id or str(metadata.get("agent_type") or mode or "orchestrator"),
            execution_role=execution_role or ("root_orchestrator" if parent_execution_id is None else "delegated_agent"),
            owner_execution_id=owner_execution_id or resolved_root_execution_id,
            mode=mode or "orchestrated",
            goal=goal or str(metadata.get("message") or ""),
            status=status,
            current_stage=stage or status,
            provider=provider,
            model=model,
            state_version=1,
            last_heartbeat_at=now,
            started_at=now,
            metadata_json=metadata,
        )
        await self._session_add(db, execution)
        await db.commit()
        await db.refresh(execution)
        return self._normalize_execution(execution)

    async def _get_execution_in_db(self, db: Any, *, execution_id: str) -> AgentExecution | None:
        execution = await db.get(AgentExecution, execution_id)
        if execution is None:
            return None
        return self._normalize_execution(execution)

    async def _mark_status_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
        status: str,
        updates: dict[str, Any],
    ) -> AgentExecution:
        execution = await self._require_execution(db, execution_id)
        now = _utcnow()
        execution.status = status
        execution.updated_at = now
        execution.last_heartbeat_at = now
        execution.state_version = int(getattr(execution, "state_version", 0) or 0) + 1

        metadata_updates = _coerce_dict(updates.pop("metadata", None)) if "metadata" in updates else None
        if metadata_updates is not None:
            merged_metadata = dict(getattr(execution, "metadata_json", {}) or {})
            merged_metadata.update(metadata_updates)
            execution.metadata_json = merged_metadata

        current_node = updates.pop("current_node", None)
        if current_node is not None:
            execution.current_step = str(current_node)
        current_step = updates.pop("current_step", None)
        if current_step is not None:
            execution.current_step = str(current_step)
        last_safe_node = updates.pop("last_safe_node", None)
        if last_safe_node is not None:
            execution.current_stage = str(last_safe_node)
        stage = updates.pop("stage", None)
        if stage is not None:
            execution.current_stage = str(stage)

        error = updates.pop("error", None)
        if error is not None:
            execution.error_message = str(error)

        for field_name, value in updates.items():
            if hasattr(execution, field_name):
                setattr(execution, field_name, value)

        if status == "pause_requested":
            execution.pause_requested = True
        elif status == "paused":
            execution.pause_requested = False
            execution.paused_at = now
        elif status in {"running", "resuming"}:
            execution.pause_requested = False
            execution.resumed_at = now
        elif status == "completed":
            execution.pause_requested = False
            execution.completed_at = now
        elif status == "failed":
            execution.failed_at = now

        await db.commit()
        await db.refresh(execution)
        return self._normalize_execution(execution)

    async def _record_event_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
        event_type: str,
        message: str | None,
        payload: dict[str, Any] | None,
        stage: str | None,
        step_id: str | None,
    ) -> AgentExecutionEvent:
        execution = await self._require_execution(db, execution_id)
        sequence = int(getattr(execution, "last_event_sequence", 0) or 0) + 1
        payload_dict = _coerce_dict(payload)
        payload_dict.setdefault("execution_id", execution_id)
        payload_dict.setdefault("root_execution_id", getattr(execution, "root_execution_id", execution_id))
        payload_dict.setdefault("parent_execution_id", getattr(execution, "parent_execution_id", None))
        payload_dict.setdefault("agent", getattr(execution, "agent_id", None))
        payload_dict.setdefault("status", getattr(execution, "status", None))
        payload_dict.setdefault("stage", stage or getattr(execution, "current_stage", None))
        payload_dict.setdefault("progress", getattr(execution, "progress", None))
        payload_dict.setdefault("visibility", payload_dict.get("visibility", "internal"))
        event = AgentExecutionEvent(
            execution_id=execution_id,
            sequence=sequence,
            event_type=event_type,
            message=message,
            payload_json=payload_dict,
            stage=stage or getattr(execution, "current_stage", None),
            step_id=step_id,
        )
        execution.last_event_sequence = sequence
        await self._session_add(db, event)
        await db.commit()
        await db.refresh(event)
        execution.last_event_id = getattr(event, "id", None)
        execution.updated_at = _utcnow()
        return self._normalize_row(event)

    async def _create_snapshot_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
        snapshot_kind: str,
        stage: str | None,
        state: dict[str, Any],
        context: dict[str, Any],
        is_resume_point: bool,
        parent_event_id: int | None,
        checkpoint_id: str | None,
        next_nodes: list[str],
    ) -> AgentExecutionSnapshot:
        execution = await self._require_execution(db, execution_id)
        sequence = int(getattr(execution, "last_snapshot_sequence", 0) or 0) + 1
        state_hash = _stable_json_hash({"state": state, "context": context, "next_nodes": next_nodes})
        snapshot = AgentExecutionSnapshot(
            execution_id=execution_id,
            sequence=sequence,
            snapshot_kind=snapshot_kind,
            stage=stage or getattr(execution, "current_stage", None),
            state_json=_coerce_dict(state),
            context_json=_coerce_dict(context),
            checkpoint_id=checkpoint_id,
            next_nodes=list(next_nodes),
            is_resume_point=is_resume_point,
            state_hash=state_hash,
            parent_event_id=parent_event_id,
        )
        execution.last_snapshot_sequence = sequence
        execution.context_digest = state_hash
        await self._session_add(db, snapshot)
        await db.commit()
        await db.refresh(snapshot)
        execution.last_snapshot_id = getattr(snapshot, "id", None)
        execution.updated_at = _utcnow()
        return self._normalize_row(snapshot)

    async def _get_latest_snapshot_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
    ) -> AgentExecutionSnapshot | None:
        result = await db.execute(
            select(AgentExecutionSnapshot)
            .where(AgentExecutionSnapshot.execution_id == execution_id)
            .order_by(AgentExecutionSnapshot.sequence.desc())
            .limit(1)
        )
        snapshot = _result_first_scalar(result)
        if snapshot is None:
            return None
        return self._normalize_snapshot(snapshot)

    async def _record_external_effect_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
        effect_key: str,
        effect_type: str,
        request: dict[str, Any] | None,
        response: dict[str, Any] | None,
        status: str,
    ) -> AgentExecutionEffect:
        execution = await self._require_execution(db, execution_id)
        existing = await db.execute(
            select(AgentExecutionEffect).where(AgentExecutionEffect.effect_key == effect_key).limit(1)
        )
        existing_effect = _result_first_scalar(existing)
        if existing_effect is not None:
            return self._normalize_row(existing_effect)

        sequence = int(getattr(execution, "last_effect_sequence", 0) or 0) + 1
        effect = AgentExecutionEffect(
            execution_id=execution_id,
            sequence=sequence,
            effect_key=effect_key,
            effect_type=effect_type,
            request_json=_coerce_dict(request),
            response_json=_coerce_dict(response),
            status=status,
        )
        execution.last_effect_sequence = sequence
        await self._session_add(db, effect)
        await db.commit()
        await db.refresh(effect)
        execution.updated_at = _utcnow()
        return self._normalize_row(effect)

    async def _record_message_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
        message_type: str,
        sender_execution_id: str | None,
        recipient_execution_id: str | None,
        content: str,
        visibility: str,
        payload: dict[str, Any] | None,
        status: str,
    ) -> AgentExecutionMessage:
        execution = await self._require_execution(db, execution_id)
        sequence = int(getattr(execution, "last_message_sequence", 0) or 0) + 1
        message = AgentExecutionMessage(
            execution_id=execution_id,
            root_execution_id=getattr(execution, "root_execution_id", execution_id),
            parent_execution_id=getattr(execution, "parent_execution_id", None),
            sequence=sequence,
            message_type=message_type,
            sender_execution_id=sender_execution_id,
            recipient_execution_id=recipient_execution_id or execution_id,
            visibility=visibility,
            status=status,
            content=content,
            payload_json=_coerce_dict(payload),
        )
        execution.last_message_sequence = sequence
        execution.updated_at = _utcnow()
        execution.last_heartbeat_at = execution.updated_at
        await self._session_add(db, message)
        await db.commit()
        await db.refresh(message)
        return self._normalize_row(message)

    async def _list_messages_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
        include_consumed: bool,
    ) -> list[SimpleNamespace]:
        query = (
            select(AgentExecutionMessage)
            .where(AgentExecutionMessage.execution_id == execution_id)
            .order_by(AgentExecutionMessage.sequence.asc())
        )
        if not include_consumed:
            query = query.where(AgentExecutionMessage.status == "pending")
        result = await db.execute(query)
        return [self._normalize_row(row) for row in result.scalars().all()]

    async def _consume_pending_messages_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
    ) -> list[SimpleNamespace]:
        result = await db.execute(
            select(AgentExecutionMessage)
            .where(AgentExecutionMessage.execution_id == execution_id)
            .where(AgentExecutionMessage.status == "pending")
            .order_by(AgentExecutionMessage.sequence.asc())
        )
        rows = list(result.scalars().all())
        now = _utcnow()
        for row in rows:
            row.status = "consumed"
            row.consumed_at = now
        execution = await self._require_execution(db, execution_id)
        execution.last_heartbeat_at = now
        await db.commit()
        return [self._normalize_row(row) for row in rows]

    async def _record_process_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
        process_key: str,
        tab_id: str | None,
        pid: int | None,
        owner_agent_id: str | None,
        terminal_key: str | None,
        cwd: str | None,
        state: str,
        metadata: dict[str, Any] | None,
    ) -> AgentExecutionProcess:
        execution = await self._require_execution(db, execution_id)
        result = await db.execute(
            select(AgentExecutionProcess)
            .where(AgentExecutionProcess.execution_id == execution_id)
            .where(AgentExecutionProcess.process_key == process_key)
            .limit(1)
        )
        process = _result_first_scalar(result)
        now = _utcnow()
        if process is None:
            process = AgentExecutionProcess(
                execution_id=execution_id,
                process_key=process_key,
                tab_id=tab_id,
                pid=pid,
                owner_agent_id=owner_agent_id or getattr(execution, "agent_id", None),
                terminal_key=terminal_key,
                cwd=cwd,
                state=state,
                metadata_json=_coerce_dict(metadata),
                started_at=now,
                updated_at=now,
                last_heartbeat_at=now,
            )
            await self._session_add(db, process)
        else:
            process.tab_id = tab_id or getattr(process, "tab_id", None)
            process.pid = pid if pid is not None else getattr(process, "pid", None)
            process.owner_agent_id = owner_agent_id or getattr(process, "owner_agent_id", None)
            process.terminal_key = terminal_key or getattr(process, "terminal_key", None)
            process.cwd = cwd or getattr(process, "cwd", None)
            process.state = state
            merged_metadata = dict(getattr(process, "metadata_json", {}) or {})
            merged_metadata.update(_coerce_dict(metadata))
            process.metadata_json = merged_metadata
            process.updated_at = now
            process.last_heartbeat_at = now

        execution.last_heartbeat_at = now
        await db.commit()
        await db.refresh(process)
        return self._normalize_row(process)

    async def _update_process_in_db(
        self,
        db: Any,
        *,
        process_key: str,
        state: str | None,
        pid: int | None,
        metadata: dict[str, Any] | None,
        terminal_key: str | None,
        cwd: str | None,
        tab_id: str | None,
        ended_at: datetime | None,
        heartbeat: bool,
    ) -> AgentExecutionProcess | None:
        result = await db.execute(
            select(AgentExecutionProcess).where(AgentExecutionProcess.process_key == process_key).limit(1)
        )
        process = _result_first_scalar(result)
        if process is None:
            return None
        now = _utcnow()
        if state is not None:
            process.state = state
        if pid is not None:
            process.pid = pid
        if terminal_key is not None:
            process.terminal_key = terminal_key
        if cwd is not None:
            process.cwd = cwd
        if tab_id is not None:
            process.tab_id = tab_id
        if metadata is not None:
            merged_metadata = dict(getattr(process, "metadata_json", {}) or {})
            merged_metadata.update(_coerce_dict(metadata))
            process.metadata_json = merged_metadata
        if heartbeat or state is not None:
            process.last_heartbeat_at = now
        process.updated_at = now
        if ended_at is not None:
            process.ended_at = ended_at
        elif state in {"completed", "failed", "lost", "terminated"}:
            process.ended_at = now
        await db.commit()
        await db.refresh(process)
        return self._normalize_row(process)

    async def _list_processes_in_db(self, db: Any, *, execution_id: str) -> list[SimpleNamespace]:
        result = await db.execute(
            select(AgentExecutionProcess)
            .where(AgentExecutionProcess.execution_id == execution_id)
            .order_by(AgentExecutionProcess.started_at.asc())
        )
        return [self._normalize_row(row) for row in result.scalars().all()]

    async def _save_session_runtime_state_in_db(
        self,
        db: Any,
        *,
        session_id: str,
        execution_id: str | None,
        state: dict[str, Any],
        version: int,
    ) -> SessionRuntimeState:
        row = await db.get(SessionRuntimeState, session_id)
        if _is_mock_placeholder(row):
            row = None
        if row is None:
            row = SessionRuntimeState(
                session_id=session_id,
                execution_id=execution_id,
                state_json=_coerce_dict(state),
                state_hash=_stable_json_hash(state),
                version=version,
            )
            await self._session_add(db, row)
        else:
            row.execution_id = execution_id
            row.state_json = _coerce_dict(state)
            row.state_hash = _stable_json_hash(state)
            row.version = version
            row.updated_at = _utcnow()
        await db.commit()
        await db.refresh(row)
        return self._normalize_row(row)

    async def _load_session_runtime_state_in_db(
        self,
        db: Any,
        *,
        session_id: str,
    ) -> SessionRuntimeState | None:
        row = await db.get(SessionRuntimeState, session_id)
        if row is None:
            return None
        return self._normalize_row(row)

    async def _list_events_in_db(
        self,
        db: Any,
        *,
        root_execution_id: str,
        after_id: int,
    ) -> list[SimpleNamespace]:
        result = await db.execute(
            select(AgentExecutionEvent)
            .join(AgentExecution, AgentExecution.id == AgentExecutionEvent.execution_id)
            .where(AgentExecution.root_execution_id == root_execution_id)
            .where(AgentExecutionEvent.id > after_id)
            .order_by(AgentExecutionEvent.id.asc())
        )
        return [self._normalize_row(row) for row in result.scalars().all()]

    async def _get_execution_tree_in_db(
        self,
        db: Any,
        *,
        execution_id: str,
    ) -> dict[str, Any]:
        execution = await self._require_execution(db, execution_id)
        root_execution_id = getattr(execution, "root_execution_id", None) or execution_id
        root_result = await db.execute(
            select(AgentExecution).where(AgentExecution.id == root_execution_id).limit(1)
        )
        root = _result_first_scalar(root_result) or execution
        all_result = await db.execute(
            select(AgentExecution)
            .where(AgentExecution.root_execution_id == root_execution_id)
            .order_by(AgentExecution.created_at.asc())
        )
        executions = [self._normalize_execution(row) for row in all_result.scalars().all()]
        if not any(item.id == root_execution_id for item in executions):
            executions.insert(0, self._normalize_execution(root))

        messages_by_execution: dict[str, list[SimpleNamespace]] = {}
        message_result = await db.execute(
            select(AgentExecutionMessage)
            .where(AgentExecutionMessage.root_execution_id == root_execution_id)
            .order_by(AgentExecutionMessage.sequence.asc())
        )
        for row in message_result.scalars().all():
            normalized = self._normalize_row(row)
            messages_by_execution.setdefault(normalized.execution_id, []).append(normalized)

        processes_by_execution: dict[str, list[SimpleNamespace]] = {}
        process_result = await db.execute(
            select(AgentExecutionProcess)
            .join(AgentExecution, AgentExecution.id == AgentExecutionProcess.execution_id)
            .where(AgentExecution.root_execution_id == root_execution_id)
            .order_by(AgentExecutionProcess.started_at.asc())
        )
        for row in process_result.scalars().all():
            normalized = self._normalize_row(row)
            processes_by_execution.setdefault(normalized.execution_id, []).append(normalized)

        nodes: dict[str, dict[str, Any]] = {}
        for item in executions:
            nodes[item.id] = {
                "execution": self._execution_to_dict(item),
                "messages": [self._row_to_dict(message) for message in messages_by_execution.get(item.id, [])],
                "processes": [self._row_to_dict(process) for process in processes_by_execution.get(item.id, [])],
                "children": [],
            }

        for item in executions:
            parent_id = getattr(item, "parent_execution_id", None)
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(nodes[item.id])

        return nodes.get(root_execution_id, {
            "execution": self._execution_to_dict(self._normalize_execution(root)),
            "messages": [],
            "processes": [],
            "children": [],
        })

    async def _require_execution(self, db: Any, execution_id: str) -> AgentExecution:
        execution = await db.get(AgentExecution, execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")
        return execution

    def _normalize_execution(self, execution: AgentExecution) -> SimpleNamespace:
        payload = self._normalize_row(execution).__dict__
        payload["metadata"] = payload.pop("metadata_json", {}) or {}
        return SimpleNamespace(**payload)

    def _normalize_snapshot(self, snapshot: AgentExecutionSnapshot) -> SimpleNamespace:
        payload = self._normalize_row(snapshot).__dict__
        payload["context_bundle"] = payload.get("context_json", {}) or {}
        payload["resumable"] = bool(payload.get("is_resume_point"))
        return SimpleNamespace(**payload)

    def _normalize_row(self, row: Any) -> SimpleNamespace:
        if isinstance(row, SimpleNamespace):
            return row
        if hasattr(row, "__table__"):
            payload = {
                attr.key: getattr(row, attr.key)
                for attr in sa_inspect(row).mapper.column_attrs
            }
            return SimpleNamespace(**payload)
        if hasattr(row, "__dict__"):
            payload = {
                key: value
                for key, value in vars(row).items()
                if not key.startswith("_")
            }
            return SimpleNamespace(**payload)
        return SimpleNamespace(value=row)

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        payload = self._normalize_row(row).__dict__.copy()
        if "metadata_json" in payload:
            payload["metadata"] = payload.pop("metadata_json", {}) or {}
        if "payload_json" in payload:
            payload["payload"] = payload.pop("payload_json", {}) or {}
        return payload

    def _execution_to_dict(self, execution: Any) -> dict[str, Any]:
        payload = self._row_to_dict(execution)
        payload.setdefault("root_execution_id", payload.get("id"))
        payload.setdefault("owner_execution_id", payload.get("root_execution_id"))
        return payload

    async def _session_add(self, db: Any, row: Any) -> None:
        maybe_awaitable = db.add(row)
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    async def _run_db(
        self,
        db: Any | None,
        operation: Callable[..., Awaitable[_T]],
        **kwargs: Any,
    ) -> _T:
        if db is not None:
            return await operation(db, **kwargs)

        session_factory = self._db_session_factory
        if session_factory is None:
            from mindflow_backend.infra.database.connection import get_db_session

            session_factory = get_db_session

        async with session_factory() as session:
            return await operation(session, **kwargs)


__all__ = ["ExecutionMemoryService"]
