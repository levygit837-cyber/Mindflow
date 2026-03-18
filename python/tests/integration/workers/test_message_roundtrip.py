from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.workers.config.queues import QueueDefinitions
from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope
from mindflow_backend.workers.infrastructure.queue_manager import QueueManager
from mindflow_backend.workers.tasks.agent_tasks import AgentTaskDefinitions, AgentTaskPublisher


class _FakeQueueManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def publish_message(
        self,
        queue_name: str,
        message_data: dict[str, object],
        priority: int | None = None,
    ) -> bool:
        self.calls.append(
            {
                "queue_name": queue_name,
                "message_data": message_data,
                "priority": priority,
            }
        )
        return True


@pytest.mark.asyncio
async def test_agent_task_publisher_emits_envelope_and_coder_worker_reads_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mindflow_backend.workers.agents import coder_worker as coder_worker_module
    from mindflow_backend.workers.tasks import agent_tasks as agent_tasks_module

    fake_queue_manager = _FakeQueueManager()
    monkeypatch.setattr(agent_tasks_module, "get_queue_manager", lambda: fake_queue_manager)
    monkeypatch.setattr(
        coder_worker_module,
        "asyncio",
        SimpleNamespace(sleep=AsyncMock()),
        raising=False,
    )

    publisher = AgentTaskPublisher()
    task = AgentTaskDefinitions.create_code_analysis_task(
        session_id="session-1",
        file_path="src/example.py",
        analysis_type="deep",
    )

    published = await publisher.publish_task(task)

    assert published is True
    assert len(fake_queue_manager.calls) == 1

    call = fake_queue_manager.calls[0]
    message_data = call["message_data"]

    assert isinstance(message_data, dict)
    assert "task_data" not in message_data
    assert message_data["schema_version"] == "1.0"
    assert message_data["payload"]["file_path"] == "src/example.py"

    worker = coder_worker_module.CoderWorker(QueueDefinitions.CODER_HIGH)
    result = await worker.process_message(message_data)

    assert result.success is True
    assert result.data["file_path"] == "src/example.py"
    assert result.data["analysis_type"] == "deep"


@pytest.mark.asyncio
async def test_queue_manager_preserves_existing_envelope_metadata_on_publish() -> None:
    publish = AsyncMock()
    manager = QueueManager()
    manager._initialized = True
    manager._channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=publish))

    envelope = QueueMessageEnvelope(
        schema_version="1.0",
        task_id="task-1",
        task_type="code_analysis",
        session_id="session-1",
        correlation_id="corr-1",
        idempotency_key="idem-1",
        created_at="2026-03-16T00:00:00Z",
        metadata={"source": "test"},
        payload={"file_path": "src/example.py", "analysis_type": "deep"},
    )

    success = await manager.publish_message(
        queue_name="coder_high",
        message_data=envelope.model_dump(mode="json"),
        priority=7,
    )

    assert success is True
    publish.assert_awaited_once()

    message = publish.await_args.args[0]
    published_body = json.loads(message.body.decode())

    assert published_body["schema_version"] == "1.0"
    assert published_body["metadata"] == {"source": "test"}
    assert published_body["payload"]["file_path"] == "src/example.py"


@pytest.mark.asyncio
async def test_coder_worker_accepts_legacy_nested_task_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mindflow_backend.workers.agents import coder_worker as coder_worker_module

    monkeypatch.setattr(
        coder_worker_module,
        "asyncio",
        SimpleNamespace(sleep=AsyncMock()),
        raising=False,
    )

    worker = coder_worker_module.CoderWorker(QueueDefinitions.CODER_HIGH)
    result = await worker.process_message(
        {
            "task_type": "code_analysis",
            "task_id": "task-legacy",
            "session_id": "session-legacy",
            "task_data": {
                "file_path": "legacy/example.py",
                "analysis_type": "legacy",
            },
            "metadata": {"source": "legacy-test"},
        }
    )

    assert result.success is True
    assert result.data["file_path"] == "legacy/example.py"
    assert result.data["analysis_type"] == "legacy"
