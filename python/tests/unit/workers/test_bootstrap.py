from __future__ import annotations

import tomllib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueDefinitions

PYTHON_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT_PATH = PYTHON_ROOT / "pyproject.toml"


class _DummyProcess:
    pid = 123

    def poll(self) -> int:
        return 0


class _DummyWorker(BaseWorker):
    async def process_message(self, message_data):
        return WorkerResult(success=True, message="ok")


def _worker_settings() -> SimpleNamespace:
    return SimpleNamespace(
        rabbitmq_url="amqp://guest:guest@127.0.0.1:5672/",
        rabbitmq_host="127.0.0.1",
        rabbitmq_port=5672,
        rabbitmq_username="guest",
        rabbitmq_password="guest",
        rabbitmq_virtual_host="/",
        prefetch_count=7,
        heartbeat=60,
        connection_timeout=5,
    )


def test_worker_entrypoints_target_main_worker() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text())
    scripts = project["project"]["scripts"]

    assert scripts["mindflow-worker"] == "mindflow_backend.workers.main:main"
    assert scripts["mindflow-new-worker"] == "mindflow_backend.workers.main:main"


def test_launcher_uses_main_worker_module_for_desktop_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindflow_desktop import launcher

    commands: list[list[str]] = []

    def fake_start_background_process(cmd, cwd, log_path):
        commands.append(cmd)
        return _DummyProcess()

    monkeypatch.setenv("MINDFLOW_START_WORKER", "1")
    monkeypatch.setenv("MINDFLOW_USE_NEW_WORKERS", "0")
    monkeypatch.setenv("MINDFLOW_DESKTOP_SKIP_UI", "1")
    monkeypatch.setattr(launcher, "_start_background_process", fake_start_background_process)
    monkeypatch.setattr(launcher, "_run_step", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(launcher, "_wait_for_api", lambda _url: None)

    launcher.run()

    assert commands[-1][-1] == "mindflow_backend.workers.main"


def test_worker_settings_read_explicit_rabbitmq_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindflow_backend.infra.config.settings import get_settings
    from mindflow_backend.workers.config.settings import get_worker_settings

    monkeypatch.setenv("RABBITMQ_URL", "amqp://mindflow:secret@rabbit.internal:5678/%2Fmindflow")
    monkeypatch.setenv("RABBITMQ_HOST", "rabbit.internal")
    monkeypatch.setenv("RABBITMQ_PORT", "5678")
    monkeypatch.setenv("RABBITMQ_USERNAME", "mindflow")
    monkeypatch.setenv("RABBITMQ_PASSWORD", "secret")
    monkeypatch.setenv("RABBITMQ_VIRTUAL_HOST", "/mindflow")

    get_settings.cache_clear()
    settings = get_settings()
    worker_settings = get_worker_settings()

    assert settings.rabbitmq_host == "rabbit.internal"
    assert settings.rabbitmq_port == 5678
    assert settings.rabbitmq_username == "mindflow"
    assert settings.rabbitmq_password == "secret"
    assert settings.rabbitmq_virtual_host == "/mindflow"
    assert worker_settings.rabbitmq_host == "rabbit.internal"
    assert worker_settings.rabbitmq_port == 5678
    assert worker_settings.rabbitmq_username == "mindflow"
    assert worker_settings.rabbitmq_password == "secret"
    assert worker_settings.rabbitmq_virtual_host == "/mindflow"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_queue_manager_uses_aio_pika_connect_robust(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindflow_backend.workers.infrastructure import queue_manager as queue_manager_module

    channel = AsyncMock()
    connection = AsyncMock()
    connection.channel = AsyncMock(return_value=channel)
    channel.set_qos = AsyncMock()

    connect_robust = AsyncMock(return_value=connection)

    monkeypatch.setattr(queue_manager_module, "get_worker_settings", _worker_settings)
    monkeypatch.setattr(queue_manager_module, "aio_pika", SimpleNamespace(connect_robust=connect_robust), raising=False)
    monkeypatch.setattr(queue_manager_module.QueueManager, "_setup_all_queues", AsyncMock())

    if hasattr(queue_manager_module, "pika"):
        monkeypatch.setattr(
            queue_manager_module.pika,
            "connect_async",
            AsyncMock(side_effect=AssertionError("pika.connect_async should not be used")),
            raising=False,
        )

    manager = queue_manager_module.QueueManager()
    await manager.initialize()

    connect_robust.assert_awaited_once()
    channel.set_qos.assert_awaited_once_with(prefetch_count=7)


@pytest.mark.asyncio
async def test_base_worker_uses_aio_pika_connect_robust(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindflow_backend.workers.base import worker as worker_module

    channel = AsyncMock()
    connection = AsyncMock()
    connection.channel = AsyncMock(return_value=channel)
    channel.set_qos = AsyncMock()

    connect_robust = AsyncMock(return_value=connection)

    monkeypatch.setattr(worker_module, "get_worker_settings", _worker_settings)
    monkeypatch.setattr(worker_module, "aio_pika", SimpleNamespace(connect_robust=connect_robust), raising=False)
    monkeypatch.setattr(_DummyWorker, "_setup_queue", AsyncMock())
    monkeypatch.setattr(_DummyWorker, "_start_consuming", AsyncMock())

    if hasattr(worker_module, "pika"):
        monkeypatch.setattr(
            worker_module.pika,
            "connect_async",
            AsyncMock(side_effect=AssertionError("pika.connect_async should not be used")),
            raising=False,
        )

    worker = _DummyWorker(QueueDefinitions.HEALTH_LOW)
    await worker.start()

    connect_robust.assert_awaited_once()
    channel.set_qos.assert_awaited_once_with(prefetch_count=7)


@pytest.mark.asyncio
async def test_run_workers_uses_worker_monitor_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindflow_backend.workers import main as workers_main

    events: list[str] = []

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

    async def stop_loop(_seconds: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(workers_main, "WorkerFactory", FakeFactory)
    monkeypatch.setattr(workers_main, "WorkerMonitor", FakeMonitor)
    monkeypatch.setattr(workers_main.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(workers_main.asyncio, "sleep", stop_loop)

    await workers_main.run_workers(["health"])

    assert events == [
        "worker.start",
        "monitor.add",
        "monitor.start",
        "monitor.stop",
        "worker.stop",
    ]
