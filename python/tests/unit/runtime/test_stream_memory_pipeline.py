"""Unit tests for the stream → memory write pipeline (Phase 3).

Validates that:
- _record_memory_message (borrowed-db pattern) no longer exists.
- _dispatch_memory_message accepts the active `db` session explicitly.
- Local fallback is awaited in the current scope; no detached task is scheduled.
- _fallback_record_memory_task opens its OWN db session when no active session is available.
- The public get_memory_service() facade is used, not SessionMemoryService directly.
- The runtime does not duplicate agent-memory writes outside the facade.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_runtime(*, memory_service=None, publisher=None):
    """Build an AgentRuntime with injected collaborators (no real I/O)."""
    from mindflow_backend.runtime.streaming.stream import AgentRuntime

    rt = AgentRuntime.__new__(AgentRuntime)
    rt._memory_service = memory_service if memory_service is not None else AsyncMock()
    rt._memory_publisher = publisher
    rt._orchestrator_graph = None
    return rt


def _make_db_mock():
    """Return an AsyncMock that acts as an async context manager for db_session()."""
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    return db


def _settings(*, memory_enabled=True, queue_enabled=False, fallback_enabled=True):
    s = MagicMock()
    s.memory_enabled = memory_enabled
    s.get_feature_flag = lambda key, default=None: {
        "rabbitmq_memory_pipeline_enabled": queue_enabled,
        "rabbitmq_memory_publish_fallback_local": fallback_enabled,
    }.get(key, default)
    return s


# ---------------------------------------------------------------------------
# Structural checks (sync — no marker needed)
# ---------------------------------------------------------------------------

class TestStructuralContracts:
    """Static / structural checks on the AgentRuntime class."""

    def test_record_memory_message_is_removed(self):
        """The old borrowed-db method must not exist."""
        from mindflow_backend.runtime.streaming.stream import AgentRuntime
        assert not hasattr(AgentRuntime, "_record_memory_message"), (
            "_record_memory_message still exists — the borrowed-db pattern was not removed"
        )

    def test_fallback_record_memory_task_exists(self):
        """The replacement method that owns its db session must exist."""
        from mindflow_backend.runtime.streaming.stream import AgentRuntime
        assert hasattr(AgentRuntime, "_fallback_record_memory_task"), (
            "_fallback_record_memory_task not found — replacement not implemented"
        )

    def test_dispatch_memory_message_accepts_db_param(self):
        """_dispatch_memory_message must receive the active db explicitly."""
        from mindflow_backend.runtime.streaming.stream import AgentRuntime
        sig = inspect.signature(AgentRuntime._dispatch_memory_message)
        assert "db" in sig.parameters, (
            "_dispatch_memory_message must accept `db` so local fallback can await in the current scope"
        )

    def test_fallback_task_has_no_db_param(self):
        """_fallback_record_memory_task must NOT receive an outer db."""
        from mindflow_backend.runtime.streaming.stream import AgentRuntime
        sig = inspect.signature(AgentRuntime._fallback_record_memory_task)
        assert "db" not in sig.parameters, (
            "_fallback_record_memory_task must not accept a db parameter"
        )

    def test_runtime_does_not_import_session_memory_service_directly(self):
        """stream.py must not instantiate SessionMemoryService() — use the facade."""
        import mindflow_backend.runtime.streaming.stream as mod
        src = inspect.getsource(mod)
        assert "SessionMemoryService()" not in src, (
            "stream.py still instantiates SessionMemoryService() directly"
        )


# ---------------------------------------------------------------------------
# _dispatch_memory_message routing
# ---------------------------------------------------------------------------

class TestDispatchMemoryMessage:
    @pytest.mark.asyncio
    async def test_local_fallback_awaits_public_facade_with_current_db(self):
        rt = _make_runtime()
        db = object()

        with patch(
            "mindflow_backend.runtime.streaming.stream.get_settings",
            return_value=_settings(queue_enabled=False),
        ), patch("asyncio.create_task", side_effect=AssertionError("local fallback must not detach a task")):
            await rt._dispatch_memory_message(
                db=db,
                session_id="s1",
                agent_id="a1",
                role="user",
                content="hi",
                source_message_id=1,
            )

        rt._memory_service.record_message.assert_awaited_once_with(
            db,
            session_id="s1",
            agent_id="a1",
            role="user",
            content="hi",
            source_message_id=1,
            idempotency_key="memory:1",
            source_status="final",
            derived_from_recall=False,
        )

    @pytest.mark.asyncio
    async def test_noop_when_memory_disabled(self):
        rt = _make_runtime()
        with patch(
            "mindflow_backend.runtime.streaming.stream.get_settings",
            return_value=_settings(memory_enabled=False),
        ):
            await rt._dispatch_memory_message(
                db=object(),
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=1,
            )
        rt._memory_service.record_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_to_queue_when_enabled(self):
        publisher = AsyncMock()
        publisher.publish_message_recorded = AsyncMock(return_value=True)
        rt = _make_runtime(publisher=publisher)
        with patch(
            "mindflow_backend.runtime.streaming.stream.get_settings",
            return_value=_settings(queue_enabled=True, fallback_enabled=False),
        ):
            await rt._dispatch_memory_message(
                db=object(),
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=1,
            )
        publisher.publish_message_recorded.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_awaited_when_queue_disabled(self):
        """Local fallback must use the current db and not schedule a detached task."""
        rt = _make_runtime()
        with patch(
            "mindflow_backend.runtime.streaming.stream.get_settings",
            return_value=_settings(queue_enabled=False),
        ), patch("asyncio.create_task", side_effect=AssertionError("must not schedule detached local task")):
            await rt._dispatch_memory_message(
                db=object(),
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=1,
            )

    @pytest.mark.asyncio
    async def test_noop_when_memory_service_none_and_queue_disabled(self):
        rt = _make_runtime(memory_service=None)
        rt._memory_service = None
        with patch(
            "mindflow_backend.runtime.streaming.stream.get_settings",
            return_value=_settings(queue_enabled=False),
        ):
            # Must not raise
            await rt._dispatch_memory_message(
                db=object(),
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=1,
            )

    @pytest.mark.asyncio
    async def test_fallback_triggered_on_publish_failure_with_fallback_enabled(self):
        publisher = AsyncMock()
        publisher.publish_message_recorded = AsyncMock(side_effect=RuntimeError("rabbit down"))
        rt = _make_runtime(publisher=publisher)

        with patch(
            "mindflow_backend.runtime.streaming.stream.get_settings",
            return_value=_settings(queue_enabled=True, fallback_enabled=True),
        ), patch("asyncio.create_task", side_effect=AssertionError("must not schedule detached local task")):
            await rt._dispatch_memory_message(
                db=object(),
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=1,
            )

        rt._memory_service.record_message.assert_awaited_once()


# ---------------------------------------------------------------------------
# _fallback_record_memory_task — fresh session guarantee
# ---------------------------------------------------------------------------

class TestFallbackRecordMemoryTask:
    @pytest.mark.asyncio
    async def test_opens_fresh_session_not_borrowed(self):
        """The task must open db_session() itself, NEVER receive an outer db."""
        svc = AsyncMock()
        svc.record_message = AsyncMock(return_value="emb-1")
        rt = _make_runtime(memory_service=svc)

        fresh_db = _make_db_mock()
        session_factory = MagicMock(return_value=fresh_db)

        with patch("mindflow_backend.runtime.streaming.stream.db_session", session_factory):
            await rt._fallback_record_memory_task(
                session_id="s1", agent_id="a1", role="user", content="hello",
                source_message_id=42, idempotency_key="memory:42",
            )

        # The factory was called — meaning a NEW session was opened
        session_factory.assert_called_once()
        # record_message was called
        svc.record_message.assert_called_once()
        # The db passed is the fresh one, not some borrowed outer db
        call_args = svc.record_message.call_args
        call_positional = call_args.args
        if call_positional:
            assert call_positional[0] is fresh_db
        else:
            assert call_args.kwargs.get("db") is fresh_db

    @pytest.mark.asyncio
    async def test_facade_called_with_correct_args(self):
        svc = AsyncMock()
        svc.record_message = AsyncMock(return_value="emb-99")
        rt = _make_runtime(memory_service=svc)

        fresh_db = _make_db_mock()
        with patch("mindflow_backend.runtime.streaming.stream.db_session", MagicMock(return_value=fresh_db)):
            await rt._fallback_record_memory_task(
                session_id="sess-X", agent_id="coder", role="assistant",
                content="done", source_message_id=7, idempotency_key="memory:7",
            )

        svc.record_message.assert_called_once_with(
            fresh_db,
            session_id="sess-X",
            agent_id="coder",
            role="assistant",
            content="done",
            source_message_id=7,
            idempotency_key="memory:7",
            source_status="final",
            derived_from_recall=False,
        )

    @pytest.mark.asyncio
    async def test_noop_when_memory_service_is_none(self):
        rt = _make_runtime(memory_service=None)
        rt._memory_service = None
        fresh_db = _make_db_mock()
        factory = MagicMock(return_value=fresh_db)
        with patch("mindflow_backend.runtime.streaming.stream.db_session", factory):
            await rt._fallback_record_memory_task(
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=None,
            )
        factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_noop_when_db_session_is_none(self):
        svc = AsyncMock()
        rt = _make_runtime(memory_service=svc)
        with patch("mindflow_backend.runtime.streaming.stream.db_session", None):
            await rt._fallback_record_memory_task(
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=None,
            )
        svc.record_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_swallows_exception_without_raising(self):
        """Exceptions in the background task must be logged, not propagated."""
        svc = AsyncMock()
        svc.record_message = AsyncMock(side_effect=RuntimeError("db error"))
        rt = _make_runtime(memory_service=svc)
        fresh_db = _make_db_mock()
        with patch("mindflow_backend.runtime.streaming.stream.db_session", MagicMock(return_value=fresh_db)):
            # Should NOT raise
            await rt._fallback_record_memory_task(
                session_id="s1", agent_id="a1", role="user", content="hi",
                source_message_id=1, idempotency_key="memory:1",
            )


# ---------------------------------------------------------------------------
# façade ownership in the same logical write path
# ---------------------------------------------------------------------------

class TestFacadeOwnership:
    """The runtime fallback delegates the write path to the facade only."""

    @pytest.mark.asyncio
    async def test_fallback_task_does_not_write_agent_memory_event_directly(self):
        svc = AsyncMock()
        svc.record_message = AsyncMock(return_value="emb-1")
        rt = _make_runtime(memory_service=svc)

        fresh_db = _make_db_mock()
        with patch("mindflow_backend.runtime.streaming.stream.db_session", MagicMock(return_value=fresh_db)), \
             patch.object(
                 rt,
                 "_write_agent_memory_event",
                 side_effect=AssertionError("runtime must not duplicate agent-memory writes"),
             ):
            await rt._fallback_record_memory_task(
                session_id="s-1", agent_id="a-1", role="user",
                content="test content for tokens", source_message_id=55,
                idempotency_key="memory:55",
            )

        svc.record_message.assert_awaited_once_with(
            fresh_db,
            session_id="s-1",
            agent_id="a-1",
            role="user",
            content="test content for tokens",
            source_message_id=55,
            idempotency_key="memory:55",
            source_status="final",
            derived_from_recall=False,
        )
