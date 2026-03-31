from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.infra.config.settings import Settings
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import (
    QueueConfig,
    QueueDefinitions,
    QueuePriority,
    WorkerDomain,
)
from mindflow_backend.workers.infrastructure.queue_manager import QueueManager
from mindflow_backend.workers.research.schemas.content_tasks import (
    build_content_synthesis_envelope,
)


class _FakeMessage:
    def __init__(self, payload: dict) -> None:
        self.body = json.dumps(payload).encode()
        self.ack = AsyncMock()
        self.reject = AsyncMock()


class _AlwaysFailWorker(BaseWorker):
    async def process_message(self, message_data: dict[str, object]) -> WorkerResult:
        return WorkerResult(success=False, message="forced failure")


@pytest.mark.asyncio
async def test_queue_manager_uses_domain_dlq_for_critical_queue() -> None:
    queue = AsyncMock()
    queue.declaration_result = SimpleNamespace(message_count=0, consumer_count=0)
    declare_queue = AsyncMock(return_value=queue)

    manager = QueueManager()
    manager._channel = SimpleNamespace(declare_queue=declare_queue)

    await manager._setup_queue(QueueDefinitions.ORCHESTRATOR_CRITICAL)

    main_call = declare_queue.await_args_list[0]
    dlq_call = declare_queue.await_args_list[1]

    assert main_call.args[0] == "mindflow.agents.orchestrator.critical"
    assert main_call.kwargs["arguments"]["x-dead-letter-routing-key"] == "mindflow.agents.dlq"
    assert dlq_call.args[0] == "mindflow.agents.dlq"


@pytest.mark.asyncio
async def test_worker_rejects_message_after_max_retries_and_relies_on_dlq_binding() -> None:
    queue_config = QueueConfig(
        name="memory_low",
        domain=WorkerDomain.SYSTEM,
        worker_type="memory",
        priority=QueuePriority.LOW,
        routing_key="system.memory.low",
        max_retries=1,
        retry_delay=0,
    )
    worker = _AlwaysFailWorker(queue_config)
    worker._channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=AsyncMock()))

    envelope = build_content_synthesis_envelope(
        session_id="session-1",
        content_sources=[{"url": "https://example.com", "text": "retry test"}],
    ).model_dump(mode="json")

    first_message = _FakeMessage(envelope)
    await worker._on_message(first_message)

    worker._channel.default_exchange.publish.assert_awaited_once()
    first_message.ack.assert_awaited_once()
    first_message.reject.assert_not_called()

    second_payload = dict(envelope)
    second_payload["retry_count"] = 1
    second_message = _FakeMessage(second_payload)
    await worker._on_message(second_message)

    second_message.reject.assert_awaited_once_with(requeue=False)
    assert queue_config.get_dead_letter_queue_name() == "mindflow.system.dlq"


@pytest.mark.asyncio
async def test_queue_manager_skips_duplicate_idempotency_key() -> None:
    publish = AsyncMock()
    manager = QueueManager()
    manager._initialized = True
    manager._channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=publish))

    envelope = build_content_synthesis_envelope(
        session_id="session-1",
        content_sources=[{"url": "https://example.com", "text": "dedupe"}],
    )

    first = await manager.publish_message(
        queue_name="content_medium",
        message_data=envelope.model_dump(mode="json"),
    )
    second = await manager.publish_message(
        queue_name="content_medium",
        message_data=envelope.model_dump(mode="json"),
    )

    assert first is True
    assert second is True
    publish.assert_awaited_once()


def test_feature_flags_gate_queue_pipelines() -> None:
    settings = Settings(
        ENABLE_RABBITMQ=False,
        QUEUE_MEMORY_PIPELINE=True,
        QUEUE_SESSION_REVIEW=True,
        QUEUE_RESEARCH_PIPELINE=True,
    )

    assert settings.get_feature_flag("rabbitmq_memory_pipeline_enabled") is False
    assert settings.get_feature_flag("rabbitmq_session_review_pipeline_enabled") is False
    assert settings.get_feature_flag("rabbitmq_research_pipeline_enabled") is False

    enabled = Settings(
        ENABLE_RABBITMQ=True,
        QUEUE_MEMORY_PIPELINE=True,
        QUEUE_SESSION_REVIEW=False,
        QUEUE_RESEARCH_PIPELINE=True,
    )

    assert enabled.get_feature_flag("rabbitmq_memory_pipeline_enabled") is True
    assert enabled.get_feature_flag("rabbitmq_session_review_pipeline_enabled") is False
    assert enabled.get_feature_flag("rabbitmq_research_pipeline_enabled") is True
