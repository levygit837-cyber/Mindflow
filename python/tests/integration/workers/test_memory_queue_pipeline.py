from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.runtime.streaming import stream as stream_module
from mindflow_backend.workers.config.queues import QueueDefinitions
from mindflow_backend.workers.system.consumers.memory_consumer import MemoryTaskConsumer
from mindflow_backend.workers.system.memory_worker import MemoryWorker
from mindflow_backend.workers.system.schemas.memory_tasks import (
    build_memory_message_recorded_envelope,
)


def _settings(*, queue_enabled: bool, fallback_enabled: bool) -> SimpleNamespace:
    feature_flags = {
        "rabbitmq_memory_pipeline_enabled": queue_enabled,
        "rabbitmq_memory_publish_fallback_local": fallback_enabled,
    }

    def get_feature_flag(name: str, default: bool = False) -> bool:
        return feature_flags.get(name, default)

    return SimpleNamespace(
        memory_enabled=True,
        feature_flags=feature_flags,
        get_feature_flag=get_feature_flag,
    )


class _FakeSessionFactory:
    def __init__(self, db: object) -> None:
        self._db = db

    def __call__(self):
        return self

    async def __aenter__(self) -> object:
        return self._db

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _message_envelope(*, idempotency_key: str = "memory:101") -> dict:
    envelope = build_memory_message_recorded_envelope(
        session_id="session-1",
        agent_id="coder",
        role="assistant",
        content="Resposta final do agente",
        source_message_id=101,
        origin="stream_runtime",
    )
    envelope.idempotency_key = idempotency_key
    envelope.task_id = idempotency_key
    envelope.correlation_id = idempotency_key

    return envelope.model_dump(mode="json")


@pytest.mark.asyncio
async def test_runtime_dispatch_publishes_memory_event_when_queue_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = stream_module.AgentRuntime()
    runtime._memory_service = object()
    runtime._memory_publisher = SimpleNamespace(
        publish_message_recorded=AsyncMock(return_value=True)
    )

    create_task = AsyncMock()

    monkeypatch.setattr(stream_module, "get_settings", lambda: _settings(queue_enabled=True, fallback_enabled=True))
    monkeypatch.setattr(stream_module.asyncio, "create_task", create_task)

    await runtime._dispatch_memory_message(
        db=object(),
        session_id="session-1",
        agent_id="coder",
        role="assistant",
        content="Resposta final do agente",
        source_message_id=101,
    )

    runtime._memory_publisher.publish_message_recorded.assert_awaited_once()
    create_task.assert_not_called()


@pytest.mark.asyncio
async def test_memory_worker_consumer_records_message(monkeypatch: pytest.MonkeyPatch) -> None:
    db = object()
    recorder = AsyncMock(return_value="embedding-1")
    consumer = MemoryTaskConsumer(
        memory_service=SimpleNamespace(record_message=recorder),
        db_session_factory=_FakeSessionFactory(db),
    )

    worker = MemoryWorker(QueueDefinitions.MEMORY_LOW)
    worker._memory_consumer = consumer

    result = await worker.process_message(_message_envelope())

    assert result.success is True
    assert result.data is not None
    assert result.data["embedding_id"] == "embedding-1"
    recorder.assert_awaited_once()
    assert recorder.await_args.kwargs["db"] is db
    assert recorder.await_args.kwargs["session_id"] == "session-1"
    assert recorder.await_args.kwargs["source_message_id"] == 101


@pytest.mark.asyncio
async def test_memory_consumer_skips_duplicate_idempotency_key() -> None:
    recorder = AsyncMock(return_value="embedding-1")
    consumer = MemoryTaskConsumer(
        memory_service=SimpleNamespace(record_message=recorder),
        db_session_factory=_FakeSessionFactory(object()),
    )
    message = _message_envelope(idempotency_key="memory:dedupe")

    first = await consumer.consume_message_recorded(message)
    second = await consumer.consume_message_recorded(message)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    recorder.assert_awaited_once()
