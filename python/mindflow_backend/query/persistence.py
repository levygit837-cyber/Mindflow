"""Execution-persistence helpers for the unified QueryEngine kernel.

Pure async functions extracted from ``AgentRuntime`` (in
``runtime/streaming/stream.py``) that handle the lifecycle of
``execution_memory`` records — creating executions, syncing session state,
and persisting chat messages.

These functions are stateless on purpose: every dependency (db sessions,
memory services, execution_memory service) is passed as an argument so they
are easy to test in isolation and can be called from both the new
``QueryEngine.execute()`` path and the legacy ``AgentRuntime`` during the
migration window.

Phase 2 of the unified-engine plan — see
.windsurf/plans/unified-engine-47796c.md §4.2.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mindflow_backend.schemas.chat.agent import AgentChatRequest
    from mindflow_backend.schemas.orchestration.orchestrator import WorkspaceBinding

_logger = get_logger(__name__)


def snapshot_json(value: Any) -> Any:
    """Recursively convert complex objects to JSON-safe primitives.

    Mirrors ``AgentRuntime._snapshot_json`` as a module-level function.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [snapshot_json(item) for item in value]
    if isinstance(value, dict):
        return {str(k): snapshot_json(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return snapshot_json(value.model_dump(mode="json"))
    if hasattr(value, "value"):
        return snapshot_json(value.value)
    return str(value)


async def start_execution(
    *,
    execution_memory: Any,
    payload: AgentChatRequest,
    session_id: str,
    run_id: str | None,
    provider: str,
    model: str,
    execution_mode: str,
    workspace_binding: WorkspaceBinding | None = None,
    execution_id: str | None = None,
    status: str = "running",
    stage: str | None = None,
) -> Any | None:
    """Create or reuse an execution record in ``execution_memory``.

    Returns the execution object on success, ``None`` when
    ``execution_memory`` is unavailable or the write fails.
    """
    if execution_memory is None:
        return None

    requested_folder_path = getattr(payload, "folder_path", None)
    metadata: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "agent_type": getattr(payload, "agent_type", None),
        "folder_path": getattr(payload, "folder_path", None),
        "requested_folder_path": requested_folder_path,
        "orchestrate": bool(getattr(payload, "orchestrate", False)),
        "message": payload.message,
    }
    if workspace_binding is not None:
        metadata["workspace"] = workspace_binding.model_dump(mode="json")

    resolved_stage = stage or ("routing" if execution_mode == "orchestrated" else "booting")

    try:
        return await execution_memory.start_execution(
            session_id=session_id,
            execution_id=execution_id or getattr(payload, "execution_id", None),
            run_id=run_id,
            mode=execution_mode,
            provider=provider,
            model=model,
            status=status,
            stage=resolved_stage,
            metadata=metadata,
        )
    except Exception as exc:
        _logger.warning(
            "execution_start_persistence_failed",
            session_id=session_id,
            mode=execution_mode,
            error=str(exc),
        )
        return None


async def sync_session_runtime_state(
    *,
    execution_memory: Any,
    session_id: str | None,
    execution_id: str | None,
) -> None:
    """Persist current agent_runtime state block to the session record.

    Safe to call with ``None`` values — it returns early when anything
    is missing. Mirrors ``AgentRuntime._sync_session_runtime_state``.
    """
    if execution_memory is None or not session_id or not execution_id:
        return

    try:
        execution = await execution_memory.get_execution(execution_id)
        if execution is None:
            return

        root_execution_id = getattr(execution, "root_execution_id", None) or execution_id
        root_execution = execution
        if root_execution_id != execution_id:
            loaded_root = await execution_memory.get_execution(root_execution_id)
            if loaded_root is not None:
                root_execution = loaded_root

        status = getattr(root_execution, "status", None)
        active = status in {"queued", "running", "pause_requested", "paused", "resuming"}
        state: dict[str, Any] = {
            "agent_runtime": {
                "latest_execution_id": execution_id,
                "latest_root_execution_id": root_execution_id,
                "active_execution_id": root_execution_id if active else None,
                "root_execution_id": root_execution_id,
                "status": status,
                "stage": getattr(root_execution, "current_stage", None),
                "progress": getattr(root_execution, "progress", None),
                "can_resume": status in {"paused", "pause_requested"},
                "active": active,
                "updated_at": snapshot_json(
                    getattr(root_execution, "updated_at", None)
                    or getattr(root_execution, "created_at", None)
                ),
            }
        }
        metadata = getattr(root_execution, "metadata", {}) or {}
        workspace = metadata.get("workspace")
        if isinstance(workspace, dict):
            state["workspace"] = {"session": workspace}

        await execution_memory.save_session_runtime_state(
            session_id=session_id,
            execution_id=root_execution_id,
            state=state,
        )
    except Exception as exc:
        _logger.warning(
            "session_runtime_state_sync_failed",
            session_id=session_id,
            execution_id=execution_id,
            error=str(exc),
        )


async def save_message_bg(
    *,
    session_id: str,
    role: str,
    content: str,
    memory_agent_id: str,
    memory_service: Any,
    db_session: Any,
    chat_message_cls: Any,
    chat_session_cls: Any,
    memory_publisher: Any = None,
    provider: str | None = None,
    model: str | None = None,
    source_status: str = "final",
    derived_from_recall: bool = False,
) -> None:
    """Deduplicated fire-and-forget DB + memory write.

    Mirrors ``AgentRuntime._save_message_bg``. All ORM classes and
    services are passed as arguments so this function has no hard
    import-time dependencies on SQLAlchemy or memory modules.
    """
    from datetime import UTC, datetime

    if db_session is None or chat_message_cls is None or chat_session_cls is None:
        return

    normalized_content = " ".join(content.split())
    if not normalized_content:
        return

    dedupe_key = hashlib.sha256(
        f"{session_id}:{role}:{provider or ''}:{model or ''}:{normalized_content}".encode()
    ).hexdigest()

    try:
        from sqlalchemy import select

        async with db_session() as db:
            sess = await db.get(chat_session_cls, session_id)
            if not sess:
                sess = chat_session_cls(id=session_id, title="New Chat")
                db.add(sess)

            existing = (
                await db.execute(
                    select(chat_message_cls)
                    .where(chat_message_cls.session_id == session_id)
                    .where(chat_message_cls.role == role)
                    .where(chat_message_cls.content == normalized_content)
                    .where(
                        chat_message_cls.provider
                        == (provider if role == "assistant" else None)
                    )
                    .where(
                        chat_message_cls.model
                        == (model if role == "assistant" else None)
                    )
                    .order_by(chat_message_cls.created_at.desc())
                    .limit(1)
                )
            ).scalars().first()

            if existing is not None:
                _logger.debug(
                    "bg_save_message_deduped",
                    session_id=session_id,
                    role=role,
                    dedupe_key=dedupe_key,
                )
                return

            msg = chat_message_cls(
                session_id=session_id,
                role=role,
                content=normalized_content,
                provider=provider if role == "assistant" else None,
                model=model if role == "assistant" else None,
            )
            db.add(msg)
            sess.updated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(msg)

            if memory_service is not None:
                await dispatch_memory_message(
                    db=db,
                    session_id=session_id,
                    agent_id=memory_agent_id,
                    role=role,
                    content=content,
                    source_message_id=msg.id,
                    memory_service=memory_service,
                    memory_publisher=memory_publisher,
                    db_session_factory=db_session,
                    source_status=source_status,
                    derived_from_recall=derived_from_recall,
                )
    except Exception as exc:
        _logger.error("bg_save_message_failed", role=role, error=str(exc))


async def dispatch_memory_message(
    *,
    db: Any,
    session_id: str,
    agent_id: str,
    role: str,
    content: str,
    source_message_id: Any,
    memory_service: Any,
    memory_publisher: Any = None,
    db_session_factory: Any = None,
    idempotency_key: str | None = None,
    source_status: str = "final",
    derived_from_recall: bool = False,
) -> None:
    """Route a message to the memory pipeline (publisher or direct write).

    Mirrors ``AgentRuntime._dispatch_memory_message``.
    """
    idempotency_key = idempotency_key or hashlib.sha256(
        f"{session_id}:{agent_id}:{role}:{content[:200]}".encode()
    ).hexdigest()

    if memory_publisher is not None:
        try:
            await memory_publisher.publish_memory_task(
                session_id=session_id,
                agent_id=agent_id,
                role=role,
                content=content,
                source_message_id=source_message_id,
                idempotency_key=idempotency_key,
                source_status=source_status,
                derived_from_recall=derived_from_recall,
            )
            return
        except Exception as exc:
            _logger.debug(
                "memory_publisher_unavailable_falling_back",
                session_id=session_id,
                error=str(exc),
            )

    if memory_service is None or db_session_factory is None:
        return
    try:
        async with db_session_factory() as fresh_db:
            await memory_service.record_message(
                fresh_db,
                session_id=session_id,
                agent_id=agent_id,
                role=role,
                content=content,
                source_message_id=source_message_id,
                idempotency_key=idempotency_key,
                source_status=source_status,
                derived_from_recall=derived_from_recall,
            )
    except Exception as exc:
        _logger.warning(
            "memory_record_failed",
            error=str(exc),
            session_id=session_id,
            agent_id=agent_id,
            role=role,
        )
