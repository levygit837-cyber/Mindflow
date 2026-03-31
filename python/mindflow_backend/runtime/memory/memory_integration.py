"""Memory Integration - Execution memory and session state persistence.

Handles execution lifecycle, memory dispatch, background message saving,
and session runtime state synchronization.
"""

from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.chat.agent import AgentChatRequest

_logger = get_logger(__name__)

try:
    from mindflow_backend.memory import get_memory_service as _get_memory_service
except Exception as exc:  # pragma: no cover
    _get_memory_service = None
    _logger.warning("memory_service_import_failed", error=str(exc))

try:
    from mindflow_backend.execution_memory import (
        get_execution_memory_service as _get_execution_memory_service,
    )
except Exception as exc:  # pragma: no cover
    _get_execution_memory_service = None
    _logger.warning("execution_memory_service_import_failed", error=str(exc))

try:
    from mindflow_backend.workers.system.publishers.memory_publisher import (
        RabbitMQMemoryTaskPublisher as _RabbitMQMemoryTaskPublisher,
    )
except Exception as exc:  # pragma: no cover
    _RabbitMQMemoryTaskPublisher = None
    _logger.warning("memory_publisher_import_failed", error=str(exc))

try:
    from mindflow_backend.infra.database.connection import get_db_session as db_session
    from mindflow_backend.storage.postgresql.models import (
        AgentMemoryEvent,
        ChatMessage,
        ChatSession,
    )
except Exception as exc:  # pragma: no cover
    db_session = None
    AgentMemoryEvent = None
    ChatMessage = None
    ChatSession = None
    _logger.warning("runtime_db_import_failed", error=str(exc))


class MemoryIntegration:
    """Handles memory operations, execution lifecycle, and session state."""

    def __init__(
        self,
        runtime: Any = None,
        memory_service: Any = None,
        execution_memory: Any = None,
        memory_publisher: Any = None,
    ) -> None:
        """Initialize with reference to parent AgentRuntime or explicit services."""
        self._runtime = runtime
        self._memory_service = memory_service or (_get_memory_service() if _get_memory_service else None)
        self._execution_memory = execution_memory or (_get_execution_memory_service() if _get_execution_memory_service else None)
        self._memory_publisher = memory_publisher or (_RabbitMQMemoryTaskPublisher() if _RabbitMQMemoryTaskPublisher else None)

    @staticmethod
    def _resolve_execution_mode(payload: AgentChatRequest) -> str:
        """Resolve execution mode from payload attributes."""
        _executor_ref = None
        if hasattr(payload, "_executor_ref"):
            _executor_ref = payload._executor_ref

        # Check if forced analyst flow
        agent_type = (getattr(payload, "agent_type", None) or "").lower()
        folder_path = getattr(payload, "folder_path", None)
        if agent_type == "analyst" and bool(folder_path):
            return "orchestrated"

        if payload.orchestrate:
            return "orchestrated"
        if getattr(payload, "agent_type", None):
            return "direct"
        return "legacy"

    @staticmethod
    def _snapshot_json(value: Any) -> Any:
        """Recursively serialize values to JSON-safe types."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [MemoryIntegration._snapshot_json(item) for item in value]
        if isinstance(value, tuple):
            return [MemoryIntegration._snapshot_json(item) for item in value]
        if isinstance(value, dict):
            return {str(key): MemoryIntegration._snapshot_json(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            return MemoryIntegration._snapshot_json(value.model_dump(mode="json"))
        if hasattr(value, "value"):
            return MemoryIntegration._snapshot_json(value.value)
        return str(value)

    def _resolve_memory_agent_id(self, payload: AgentChatRequest) -> str:
        """Resolve agent ID for memory bucketing using static heuristic."""
        if payload.agent_type:
            return payload.agent_type
        if payload.orchestrate:
            return "orchestrator"
        return "general"

    async def save_message_bg(
        self,
        session_id: str,
        role: str,
        content: str,
        memory_agent_id: str,
        provider: str | None = None,
        model: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> None:
        """Fire-and-forget DB + memory write — runs in background task."""
        if db_session is None or ChatMessage is None or ChatSession is None:
            return
        try:
            async with db_session() as db:
                # Ensure session exists
                sess = await db.get(ChatSession, session_id)
                if not sess:
                    sess = ChatSession(id=session_id, title="New Chat")
                    db.add(sess)

                msg = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    provider=provider if role == "assistant" else None,
                    model=model if role == "assistant" else None,
                )
                db.add(msg)
                sess.updated_at = datetime.now(UTC)
                await db.commit()
                await db.refresh(msg)

                await self.dispatch_memory_message(
                    db=db,
                    session_id=session_id,
                    agent_id=memory_agent_id,
                    role=role,
                    content=content,
                    source_message_id=msg.id,
                    source_status=source_status,
                    derived_from_recall=derived_from_recall,
                )
        except Exception as exc:
            _logger.error("bg_save_message_failed", role=role, error=str(exc))

    async def start_execution(
        self,
        *,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None,
        provider: str,
        model: str,
        execution_id: str | None = None,
        status: str = "running",
        stage: str | None = None,
    ) -> Any | None:
        """Create an execution record in the execution memory service."""
        if self._execution_memory is None:
            return None

        execution_mode = self._resolve_execution_mode(payload)
        metadata: dict[str, Any] = {
            "provider": provider,
            "model": model,
            "agent_type": getattr(payload, "agent_type", None),
            "folder_path": getattr(payload, "folder_path", None),
            "orchestrate": bool(payload.orchestrate),
            "message": payload.message,
        }

        try:
            return await self._execution_memory.start_execution(
                session_id=session_id,
                execution_id=execution_id or getattr(payload, "execution_id", None),
                run_id=run_id,
                mode=execution_mode,
                provider=provider,
                model=model,
                status=status,
                stage=stage or ("routing" if execution_mode == "orchestrated" else "booting"),
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

    async def dispatch_memory_message(
        self,
        *,
        db,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> None:
        """Dispatch memory recording via RabbitMQ publisher or fallback local."""
        settings = get_settings()
        if not settings.memory_enabled:
            return

        queue_enabled = settings.get_feature_flag("rabbitmq_memory_pipeline_enabled", False)
        fallback_enabled = settings.get_feature_flag("rabbitmq_memory_publish_fallback_local", True)

        if queue_enabled and self._memory_publisher is not None:
            try:
                published = await self._memory_publisher.publish_message_recorded(
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                    content=content,
                    source_message_id=source_message_id,
                    source_status=source_status,
                    derived_from_recall=derived_from_recall,
                )
                if published:
                    return
                if not fallback_enabled:
                    return
            except Exception as exc:
                _logger.warning(
                    "memory_publish_failed",
                    error=str(exc),
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                )
                if not fallback_enabled:
                    return

        if self._memory_service is None:
            return

        idempotency_key = f"memory:{source_message_id}" if source_message_id is not None else None

        if db is not None:
            try:
                await self._memory_service.record_message(
                    db,
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
                _logger.warning(
                    "memory_record_with_current_db_failed",
                    error=str(exc),
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                )

        await self._fallback_record_memory_task(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            source_message_id=source_message_id,
            idempotency_key=idempotency_key,
            source_status=source_status,
            derived_from_recall=derived_from_recall,
        )

    async def _fallback_record_memory_task(
        self,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None,
        idempotency_key: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> None:
        """Memory fallback — opens a fresh db session owned by this task."""
        if self._memory_service is None or db_session is None:
            return
        try:
            async with db_session() as fresh_db:
                await self._memory_service.record_message(
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

    async def _write_agent_memory_event(
        self,
        db,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None,
    ) -> None:
        """Write directly to agent_memory_events using an async session."""
        if AgentMemoryEvent is None:
            return
        from sqlalchemy import select

        from mindflow_backend.utils.core import estimate_token_count

        token_count = estimate_token_count(content)
        if token_count <= 0:
            return

        # Dedup by source_message_id when available
        if source_message_id is not None:
            existing = (
                await db.execute(
                    select(AgentMemoryEvent)
                    .where(
                        AgentMemoryEvent.session_id == session_id,
                        AgentMemoryEvent.agent_id == agent_id,
                        AgentMemoryEvent.source_message_id == source_message_id,
                    )
                    .limit(1)
                )
            ).scalars().first()
            if existing is not None:
                return

        event = AgentMemoryEvent(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
            source_message_id=source_message_id,
        )
        db.add(event)
        await db.commit()

    async def sync_session_runtime_state(
        self,
        *,
        session_id: str | None,
        execution_id: str | None,
    ) -> None:
        """Sync session runtime state with latest execution info."""
        if self._execution_memory is None or not session_id or not execution_id:
            return
        try:
            execution = await self._execution_memory.get_execution(execution_id)
            if execution is None:
                return

            root_execution_id = getattr(execution, "root_execution_id", None) or execution_id
            root_execution = execution
            if root_execution_id != execution_id:
                loaded_root = await self._execution_memory.get_execution(root_execution_id)
                if loaded_root is not None:
                    root_execution = loaded_root

            status = getattr(root_execution, "status", None)
            active = status in {"queued", "running", "pause_requested", "paused", "resuming"}
            state = {
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
                    "updated_at": self._snapshot_json(
                        getattr(root_execution, "updated_at", None)
                        or getattr(root_execution, "created_at", None)
                    ),
                }
            }
            await self._execution_memory.save_session_runtime_state(
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