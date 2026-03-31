"""Unit tests for MemoryTaskConsumer (Phase 3).

Validates that:
- Consumer uses get_memory_service() facade, NOT SessionMemoryService() directly.
- consume_message_recorded calls facade.record_message with correct args.
- Idempotency status comes from the facade/DB contract, not an in-memory set.
- The consumer does not duplicate agent_memory writes outside the facade.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.schemas.memory.contracts import MemoryPersistResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def envelope_data():
    return {
        "schema_version": "1.0",
        "task_id": "memory:42",
        "task_type": "memory.message.recorded",
        "session_id": "sess-abc",
        "run_id": None,
        "correlation_id": "memory:42",
        "idempotency_key": "memory:42",
        "created_at": datetime.now(UTC).isoformat(),
        "metadata": {},
        "payload": {
            "session_id": "sess-abc",
            "agent_id": "orchestrator",
            "role": "user",
            "content": "hello world from test",
            "source_message_id": 42,
            "content_hash": "abc123",
            "origin": "stream_runtime",
        },
    }


@pytest.fixture()
def raw_payload_data():
    return {
        "session_id": "sess-xyz",
        "agent_id": "coder",
        "role": "assistant",
        "content": "task completed successfully",
        "source_message_id": 7,
        "content_hash": "def456",
        "origin": "stream_runtime",
        "idempotency_key": "memory:7",
    }


def _make_consumer(svc=None):
    """Build a MemoryTaskConsumer with mocked collaborators."""
    svc = svc or AsyncMock()
    if not hasattr(svc.record_message, "return_value") or svc.record_message.return_value is None:
        svc.record_message = AsyncMock(return_value=MemoryPersistResult(embedding_id="emb-1"))

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(first=MagicMock(return_value=None))
            )
        )
    )
    db.add = MagicMock()
    db.commit = AsyncMock()

    db_factory = MagicMock(return_value=db)

    from mindflow_backend.workers.system.consumers.memory_consumer import MemoryTaskConsumer

    consumer = MemoryTaskConsumer(memory_service=svc, db_session_factory=db_factory)
    return consumer, db


# ---------------------------------------------------------------------------
# Structural / facade contract
# ---------------------------------------------------------------------------

class TestFacadeContract:
    def test_consumer_does_not_instantiate_session_memory_service_directly(self):
        """The consumer must NOT call SessionMemoryService() as its default service."""
        import mindflow_backend.workers.system.consumers.memory_consumer as mod

        src = inspect.getsource(mod)
        assert "SessionMemoryService()" not in src, (
            "memory_consumer.py still instantiates SessionMemoryService() directly. "
            "Must use get_memory_service() facade."
        )

    def test_consumer_defaults_to_facade(self):
        """When no service is injected, consumer must obtain it via get_memory_service()."""
        fake_svc = MagicMock()
        fake_svc.record_message = AsyncMock(return_value=MemoryPersistResult(embedding_id="emb-x"))

        with patch(
            "mindflow_backend.workers.system.consumers.memory_consumer._get_memory_service",
            return_value=fake_svc,
        ):
            from mindflow_backend.workers.system.consumers.memory_consumer import MemoryTaskConsumer
            consumer = MemoryTaskConsumer()

        assert consumer._memory_service is fake_svc

    def test_consumer_accepts_injected_service(self):
        """Injected service overrides facade (enables test isolation)."""
        injected = AsyncMock()
        injected.record_message = AsyncMock(return_value=MemoryPersistResult(embedding_id="e"))

        from mindflow_backend.workers.system.consumers.memory_consumer import MemoryTaskConsumer

        consumer = MemoryTaskConsumer(memory_service=injected)
        assert consumer._memory_service is injected


# ---------------------------------------------------------------------------
# consume_message_recorded — happy path
# ---------------------------------------------------------------------------

class TestConsumeMessageRecorded:
    @pytest.mark.asyncio
    async def test_envelope_format_returns_processed(self, envelope_data):
        consumer, _ = _make_consumer()
        result = await consumer.consume_message_recorded(envelope_data)
        assert result["status"] == "processed"
        assert result["idempotency_key"] == "memory:42"
        assert result["source_message_id"] == 42

    @pytest.mark.asyncio
    async def test_raw_payload_format_returns_processed(self, raw_payload_data):
        consumer, _ = _make_consumer()
        result = await consumer.consume_message_recorded(raw_payload_data)
        assert result["status"] == "processed"
        assert result["source_message_id"] == 7

    @pytest.mark.asyncio
    async def test_calls_facade_record_message_with_correct_args(self, envelope_data):
        svc = AsyncMock()
        svc.record_message = AsyncMock(return_value=MemoryPersistResult(embedding_id="emb-999"))
        consumer, db = _make_consumer(svc=svc)

        await consumer.consume_message_recorded(envelope_data)

        svc.record_message.assert_called_once_with(
            db,
            session_id="sess-abc",
            agent_id="orchestrator",
            role="user",
            content="hello world from test",
            source_message_id=42,
            idempotency_key="memory:42",
            source_status="final",
            derived_from_recall=False,
        )

    @pytest.mark.asyncio
    async def test_embedding_id_in_result(self, envelope_data):
        svc = AsyncMock()
        svc.record_message = AsyncMock(
            return_value=MemoryPersistResult(embedding_id="emb-555", event_id=12)
        )
        consumer, _ = _make_consumer(svc=svc)

        result = await consumer.consume_message_recorded(envelope_data)

        assert result["embedding_id"] == "emb-555"
        assert result["event_id"] == 12

    @pytest.mark.asyncio
    async def test_consumer_does_not_manually_write_agent_memory_event(self, envelope_data):
        svc = AsyncMock()
        svc.record_message = AsyncMock(return_value=MemoryPersistResult(embedding_id="emb-555"))
        consumer, _ = _make_consumer(svc=svc)

        with patch.object(
            consumer,
            "_write_agent_memory_event",
            side_effect=AssertionError("consumer must not duplicate agent-memory writes"),
            create=True,
        ):
            result = await consumer.consume_message_recorded(envelope_data)

        assert result["status"] == "processed"


# ---------------------------------------------------------------------------
# Idempotency dedup
# ---------------------------------------------------------------------------

class TestIdempotencyDedup:
    @pytest.mark.asyncio
    async def test_duplicate_status_is_driven_by_facade_result(self, envelope_data):
        svc = AsyncMock()
        svc.record_message = AsyncMock(
            side_effect=[
                MemoryPersistResult(embedding_id="emb-1"),
                MemoryPersistResult(embedding_id="emb-1", was_deduplicated=True),
            ]
        )
        consumer, _ = _make_consumer(svc=svc)

        first = await consumer.consume_message_recorded(envelope_data)
        result = await consumer.consume_message_recorded(envelope_data)

        assert first["status"] == "processed"
        assert result["status"] == "duplicate"

    @pytest.mark.asyncio
    async def test_duplicate_still_calls_facade_and_relies_on_db_idempotency(self, envelope_data):
        svc = AsyncMock()
        svc.record_message = AsyncMock(
            side_effect=[
                MemoryPersistResult(embedding_id="emb-1"),
                MemoryPersistResult(embedding_id="emb-1", was_deduplicated=True),
            ]
        )
        consumer, _ = _make_consumer(svc=svc)

        await consumer.consume_message_recorded(envelope_data)
        await consumer.consume_message_recorded(envelope_data)

        assert svc.record_message.call_count == 2

    @pytest.mark.asyncio
    async def test_different_idempotency_keys_processed_separately(
        self, envelope_data, raw_payload_data
    ):
        consumer, _ = _make_consumer()
        r1 = await consumer.consume_message_recorded(envelope_data)
        r2 = await consumer.consume_message_recorded(raw_payload_data)
        assert r1["status"] == "processed"
        assert r2["status"] == "processed"


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_raises_when_no_db_factory(self, envelope_data):
        from mindflow_backend.workers.system.consumers.memory_consumer import MemoryTaskConsumer

        consumer = MemoryTaskConsumer(
            memory_service=AsyncMock(),
            db_session_factory=None,
        )
        with pytest.raises(RuntimeError, match="No database session factory"):
            await consumer.consume_message_recorded(envelope_data)


# ---------------------------------------------------------------------------
