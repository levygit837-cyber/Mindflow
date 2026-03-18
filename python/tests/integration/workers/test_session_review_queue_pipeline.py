from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.schemas.session.review import ReviewPriority, SessionReviewResult
from mindflow_backend.services.session_review_service import SessionReviewService
from mindflow_backend.workers.config.queues import QueueConfig, QueueDefinitions, QueuePriority, WorkerDomain
from mindflow_backend.workers.system.consumers.session_review_consumer import (
    SessionReviewTaskConsumer,
)
from mindflow_backend.workers.system.schemas.session_review_tasks import (
    build_session_review_requested_envelope,
)
from mindflow_backend.workers.system.session_review_worker import SessionReviewWorker


def _settings(*, queue_enabled: bool, fallback_enabled: bool) -> SimpleNamespace:
    feature_flags = {
        "rabbitmq_session_review_pipeline_enabled": queue_enabled,
        "rabbitmq_session_review_publish_fallback_local": fallback_enabled,
    }

    def get_feature_flag(name: str, default: bool = False) -> bool:
        return feature_flags.get(name, default)

    return SimpleNamespace(
        feature_flags=feature_flags,
        get_feature_flag=get_feature_flag,
    )


def _review_result(*, session_id: str = "session-1", window_range: tuple[int, int] = (0, 10_000)) -> SessionReviewResult:
    return SessionReviewResult(
        review_id="review-1",
        session_id=session_id,
        window_range=window_range,
        priority=ReviewPriority.MEDIUM,
        summary_text="Resumo da janela",
        actions_documented=["registrar ação"],
        insights_extracted=["registrar insight"],
        review_data={"summary": "Resumo da janela"},
    )


@pytest.mark.asyncio
async def test_threshold_publishes_session_review_requested_when_queue_enabled() -> None:
    publisher = SimpleNamespace(
        publish_review_requested=AsyncMock(return_value=True)
    )
    review_agent = SimpleNamespace(
        review_session_window=AsyncMock(return_value=_review_result())
    )
    service = SessionReviewService(
        settings=_settings(queue_enabled=True, fallback_enabled=True),
        review_agent=review_agent,
        review_publisher=publisher,
    )

    await service.initialize_session_review("session-1")
    progress = await service.update_token_count("session-1", 10_000)

    publisher.publish_review_requested.assert_awaited_once()
    review_agent.review_session_window.assert_not_called()
    assert progress.window_index == 1
    assert progress.tokens_until_next_review == 10_000


@pytest.mark.asyncio
async def test_flag_off_keeps_inline_session_review_execution() -> None:
    publisher = SimpleNamespace(
        publish_review_requested=AsyncMock(return_value=True)
    )
    review_agent = SimpleNamespace(
        review_session_window=AsyncMock(return_value=_review_result())
    )
    service = SessionReviewService(
        settings=_settings(queue_enabled=False, fallback_enabled=True),
        review_agent=review_agent,
        review_publisher=publisher,
    )

    await service.initialize_session_review("session-1")
    progress = await service.update_token_count("session-1", 10_000)

    publisher.publish_review_requested.assert_not_called()
    review_agent.review_session_window.assert_awaited_once()
    assert progress.window_index == 1


@pytest.mark.asyncio
async def test_session_review_worker_consumer_executes_review_and_persists_result() -> None:
    result = _review_result()
    executor = AsyncMock(return_value=result)
    persister = AsyncMock(return_value="review-1")
    consumer = SessionReviewTaskConsumer(
        review_executor=executor,
        result_persister=persister,
        timeout_seconds=1.0,
    )

    worker = SessionReviewWorker(QueueDefinitions.SESSION_REVIEW_HIGH)
    worker._session_review_consumer = consumer

    message = build_session_review_requested_envelope(
        session_id="session-1",
        window_index=0,
        window_range=(0, 10_000),
        trigger_type="automatic_threshold",
        priority="medium",
        tokens_in_window=10_000,
        total_tokens_processed=10_000,
        threshold=10_000,
    ).model_dump(mode="json")

    processed = await worker.process_message(message)

    assert processed.success is True
    assert processed.data is not None
    assert processed.data["review_id"] == "review-1"
    executor.assert_awaited_once()
    persister.assert_awaited_once_with(result)


class _FakeMessage:
    def __init__(self, payload: dict) -> None:
        self.body = json.dumps(payload).encode()
        self.ack = AsyncMock()
        self.reject = AsyncMock()


@pytest.mark.asyncio
async def test_session_review_timeout_retries_then_rejects_to_dlq() -> None:
    consumer = SessionReviewTaskConsumer(
        review_executor=AsyncMock(side_effect=asyncio.TimeoutError("timeout")),
        result_persister=AsyncMock(),
        timeout_seconds=0.01,
    )
    queue_config = QueueConfig(
        name="session_review_high",
        domain=WorkerDomain.SYSTEM,
        worker_type="session_review",
        priority=QueuePriority.HIGH,
        routing_key="system.session_review.high",
        max_retries=1,
        retry_delay=0,
    )
    worker = SessionReviewWorker(queue_config)
    worker._session_review_consumer = consumer
    worker._channel = SimpleNamespace(
        default_exchange=SimpleNamespace(publish=AsyncMock())
    )

    first_payload = build_session_review_requested_envelope(
        session_id="session-1",
        window_index=0,
        window_range=(0, 10_000),
        trigger_type="automatic_threshold",
        priority="medium",
        tokens_in_window=10_000,
        total_tokens_processed=10_000,
        threshold=10_000,
    ).model_dump(mode="json")
    first_message = _FakeMessage(first_payload)

    await worker._on_message(first_message)

    worker._channel.default_exchange.publish.assert_awaited_once()
    first_message.ack.assert_awaited_once()
    first_message.reject.assert_not_called()

    retry_payload = dict(first_payload)
    retry_payload["retry_count"] = 1
    second_message = _FakeMessage(retry_payload)

    await worker._on_message(second_message)

    second_message.reject.assert_awaited_once_with(requeue=False)
