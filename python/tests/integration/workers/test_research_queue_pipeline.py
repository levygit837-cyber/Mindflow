from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.services.core.pinchtab_fleet_service import PinchTabFleetService
from mindflow_backend.workers.config.queues import (
    QueueConfig,
    QueueDefinitions,
    QueuePriority,
    WorkerDomain,
)
from mindflow_backend.workers.research.browser_worker import BrowserWorker
from mindflow_backend.workers.research.content_worker import ContentWorker
from mindflow_backend.workers.research.publishers.browser_publisher import (
    RabbitMQBrowserTaskPublisher,
)
from mindflow_backend.workers.research.publishers.content_publisher import (
    RabbitMQContentTaskPublisher,
)
from mindflow_backend.workers.research.schemas.browser_tasks import (
    build_web_search_envelope,
)
from mindflow_backend.workers.research.schemas.content_tasks import (
    build_content_synthesis_envelope,
)


class _FakeMessage:
    def __init__(self, payload: dict) -> None:
        self.body = json.dumps(payload).encode()
        self.ack = AsyncMock()
        self.reject = AsyncMock()


@pytest.mark.asyncio
async def test_pinchtab_fleet_service_routes_browser_and_content_jobs_to_separate_queues() -> None:
    browser_queue_manager = SimpleNamespace(publish_message=AsyncMock(return_value=True))
    content_queue_manager = SimpleNamespace(publish_message=AsyncMock(return_value=True))
    service = PinchTabFleetService(
        container_orchestrator=SimpleNamespace(),
        browser_service=SimpleNamespace(),
        session_factory=lambda: None,
        browser_task_publisher=RabbitMQBrowserTaskPublisher(queue_manager=browser_queue_manager),
        content_task_publisher=RabbitMQContentTaskPublisher(queue_manager=content_queue_manager),
    )

    browser_ok = await service.queue_web_search(
        session_id="session-1",
        query="rabbitmq worker concurrency",
        max_results=5,
    )
    content_ok = await service.queue_content_synthesis(
        session_id="session-1",
        content_sources=[{"url": "https://example.com", "text": "queue research"}],
        synthesis_type="brief",
    )

    assert browser_ok is True
    assert content_ok is True

    browser_call = browser_queue_manager.publish_message.await_args.kwargs
    content_call = content_queue_manager.publish_message.await_args.kwargs

    assert browser_call["queue_name"] == "browser_high"
    assert browser_call["message_data"]["task_type"] == "web_search"
    assert browser_call["message_data"]["session_id"] == "session-1"

    assert content_call["queue_name"] == "content_medium"
    assert content_call["message_data"]["task_type"] == "content_synthesis"
    assert content_call["message_data"]["session_id"] == "session-1"


@pytest.mark.asyncio
async def test_browser_worker_limits_concurrency_and_propagates_session_id() -> None:
    queue_config = QueueConfig(
        name="browser_high",
        domain=WorkerDomain.RESEARCH,
        worker_type="browser",
        priority=QueuePriority.HIGH,
        routing_key="research.browser.high",
        concurrency=1,
        max_retries=2,
        retry_delay=0,
    )
    worker = BrowserWorker(queue_config)

    started_sessions: list[str] = []
    release_first = asyncio.Event()
    first_started = asyncio.Event()
    active = 0
    max_active = 0

    async def consume_browser_task(message_data: dict) -> dict:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        started_sessions.append(message_data["session_id"])
        first_started.set()
        if len(started_sessions) == 1:
            await release_first.wait()
        await asyncio.sleep(0)
        active -= 1
        return {
            "status": "processed",
            "session_id": message_data["session_id"],
            "task_type": message_data["task_type"],
        }

    worker._browser_consumer = SimpleNamespace(consume_browser_task=consume_browser_task)

    first_message = build_web_search_envelope(
        session_id="session-1",
        query="first query",
    ).model_dump(mode="json")
    second_message = build_web_search_envelope(
        session_id="session-2",
        query="second query",
    ).model_dump(mode="json")

    first_task = asyncio.create_task(worker.process_message(first_message))
    await first_started.wait()
    second_task = asyncio.create_task(worker.process_message(second_message))

    await asyncio.sleep(0.05)
    assert max_active == 1
    assert started_sessions == ["session-1"]

    release_first.set()

    first_result = await first_task
    second_result = await second_task

    assert first_result.success is True
    assert second_result.success is True
    assert first_result.data is not None
    assert second_result.data is not None
    assert first_result.data["session_id"] == "session-1"
    assert second_result.data["session_id"] == "session-2"


@pytest.mark.asyncio
async def test_browser_worker_retries_transient_browser_failures() -> None:
    queue_config = QueueConfig(
        name="browser_high",
        domain=WorkerDomain.RESEARCH,
        worker_type="browser",
        priority=QueuePriority.HIGH,
        routing_key="research.browser.high",
        concurrency=1,
        max_retries=1,
        retry_delay=0,
    )
    worker = BrowserWorker(queue_config)
    worker._browser_consumer = SimpleNamespace(
        consume_browser_task=AsyncMock(side_effect=RuntimeError("temporary browser failure"))
    )
    worker._channel = SimpleNamespace(
        default_exchange=SimpleNamespace(publish=AsyncMock())
    )

    message = _FakeMessage(
        build_web_search_envelope(
            session_id="session-1",
            query="retryable browser search",
        ).model_dump(mode="json")
    )

    await worker._on_message(message)

    worker._channel.default_exchange.publish.assert_awaited_once()
    message.ack.assert_awaited_once()
    message.reject.assert_not_called()


@pytest.mark.asyncio
async def test_content_pipeline_runs_independently_from_browser_pipeline() -> None:
    worker = ContentWorker(QueueDefinitions.CONTENT_MEDIUM)
    content_consumer = AsyncMock(
        return_value={
            "status": "processed",
            "session_id": "session-1",
            "synthesized_content": "queue-safe summary",
            "source_count": 1,
        }
    )
    worker._content_consumer = SimpleNamespace(
        consume_content_synthesis=content_consumer
    )

    message = build_content_synthesis_envelope(
        session_id="session-1",
        content_sources=[{"url": "https://example.com", "text": "source"}],
    ).model_dump(mode="json")

    result = await worker.process_message(message)

    assert result.success is True
    assert result.data is not None
    assert result.data["session_id"] == "session-1"
    assert result.data["source_count"] == 1
    content_consumer.assert_awaited_once()
