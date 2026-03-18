from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from mindflow_backend.infra.logging.structured import clear_correlation_id, set_correlation_id
from mindflow_backend.workers.base.worker import WorkerStatus
from mindflow_backend.workers.config.queues import QueueDefinitions
from mindflow_backend.workers.infrastructure.monitoring import WorkerMonitor


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "rabbitmq-rollout.md"


class _FakeWorker:
    def __init__(self) -> None:
        self.worker_name = "memory_worker"
        self.queue_config = QueueDefinitions.MEMORY_LOW
        self.status = WorkerStatus.IDLE
        self._connection = SimpleNamespace(is_closed=False)
        self._channel = SimpleNamespace(is_closed=False)
        self._queue = SimpleNamespace(
            declaration_result=SimpleNamespace(message_count=4, consumer_count=1)
        )

    def get_status(self) -> WorkerStatus:
        return self.status

    def get_processing_time(self) -> float:
        return 0.0

    def get_metrics_snapshot(self) -> dict[str, object]:
        return {
            "tasks_processed": 5,
            "tasks_successful": 4,
            "tasks_failed": 1,
            "average_processing_time": 0.75,
            "last_activity": 1_700_000_000.0,
            "retry_count": 2,
            "memory_usage_mb": 64.0,
            "cpu_usage": 0.2,
            "last_correlation_id": "corr-worker-1",
        }


@pytest.mark.asyncio
async def test_worker_monitor_builds_typed_health_report_with_queue_metrics() -> None:
    monitor = WorkerMonitor(monitoring_interval=1)
    monitor.add_worker(_FakeWorker())

    await monitor.collect_once()
    report = monitor.get_health_report()

    assert report.total_workers == 1
    assert report.rabbitmq.connection_status == "connected"
    assert report.rabbitmq.channel_status == "open"
    assert len(report.workers) == 1
    assert report.workers[0].worker_name == "memory_worker"
    assert report.workers[0].tasks_processed == 5
    assert report.workers[0].retry_count == 2
    assert report.workers[0].last_correlation_id == "corr-worker-1"

    queue_report = report.queues["mindflow.system.memory.low"]
    assert queue_report.message_count == 4
    assert queue_report.consumer_count == 1
    assert queue_report.retry_count == 2
    assert queue_report.retry_rate == pytest.approx(0.4)
    assert queue_report.dead_letter_queue == "mindflow.system.dlq"


@pytest.mark.asyncio
async def test_worker_monitor_uses_current_correlation_id_in_health_report() -> None:
    monitor = WorkerMonitor(monitoring_interval=1)
    monitor.add_worker(_FakeWorker())

    set_correlation_id("corr-health-123")
    try:
        await monitor.collect_once()
        report = monitor.get_health_report()
    finally:
        clear_correlation_id()

    assert report.correlation_id == "corr-health-123"


@pytest.mark.asyncio
async def test_run_workers_collects_and_logs_startup_health_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindflow_backend.workers import main as workers_main

    events: list[str] = []
    logged_reports: list[dict[str, object]] = []

    class FakeWorker:
        async def start(self) -> None:
            events.append("worker.start")

        async def stop(self) -> None:
            events.append("worker.stop")

    class FakeFactory:
        def __init__(self) -> None:
            self._worker_registry = {"health": object()}

        def create_worker(self, worker_type: str) -> FakeWorker:
            assert worker_type == "health"
            return FakeWorker()

    class FakeMonitor:
        def __init__(self) -> None:
            self._workers = {}

        def add_worker(self, worker: FakeWorker) -> None:
            self._workers["health"] = worker
            events.append("monitor.add")

        async def start_monitoring(self) -> None:
            events.append("monitor.start")

        async def stop_monitoring(self) -> None:
            events.append("monitor.stop")

        async def collect_once(self) -> None:
            events.append("monitor.collect")

        def get_health_report(self):
            events.append("monitor.report")
            return SimpleNamespace(
                model_dump=lambda mode="json": {
                    "rabbitmq": {"connection_status": "connected"},
                    "total_workers": 1,
                }
            )

    class FakeLogger:
        def info(self, message: str, **kwargs) -> None:
            if message == "Worker startup health snapshot":
                logged_reports.append(kwargs["health_report"])

        def error(self, *_args, **_kwargs) -> None:
            return None

    async def stop_loop(_seconds: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(workers_main, "WorkerFactory", FakeFactory)
    monkeypatch.setattr(workers_main, "WorkerMonitor", FakeMonitor)
    monkeypatch.setattr(workers_main, "_logger", FakeLogger())
    monkeypatch.setattr(workers_main.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(workers_main.asyncio, "sleep", stop_loop)

    await workers_main.run_workers(["health"])

    assert events == [
        "worker.start",
        "monitor.add",
        "monitor.start",
        "monitor.collect",
        "monitor.report",
        "monitor.stop",
        "worker.stop",
    ]
    assert logged_reports == [{"rabbitmq": {"connection_status": "connected"}, "total_workers": 1}]


def test_rabbitmq_runbook_documents_rollback_and_sync_fallback() -> None:
    assert RUNBOOK_PATH.exists()

    content = RUNBOOK_PATH.read_text(encoding="utf-8").lower()

    assert "rollback" in content
    assert "fallback" in content
    assert "enable_rabbitmq" in content
    assert "queue_memory_pipeline" in content
    assert "queue_session_review" in content
    assert "queue_research_pipeline" in content
