from __future__ import annotations

import importlib

from mindflow_backend.workers.config.queues import QueueDefinitions, get_all_queue_configs
from mindflow_backend.workers.infrastructure.worker_factory import WorkerFactory
from mindflow_backend.workers.system import SessionReviewWorker


def test_session_review_queue_definition_exists() -> None:
    queue = QueueDefinitions.SESSION_REVIEW_HIGH

    assert queue.name == "session_review_high"
    assert queue.worker_type == "session_review"
    assert queue.routing_key == "system.session_review.high"


def test_worker_factory_registers_session_review_with_default_queue() -> None:
    factory = WorkerFactory()

    assert "session_review" in factory.get_supported_worker_types()

    worker = factory.create_worker("session_review")

    assert isinstance(worker, SessionReviewWorker)
    assert worker.queue_config.name == "session_review_high"


def test_system_workers_using_asyncio_import_it() -> None:
    modules = [
        "mindflow_backend.workers.system.health_worker",
        "mindflow_backend.workers.system.memory_worker",
        "mindflow_backend.workers.system.session_review_worker",
        "mindflow_backend.workers.system.vector_worker",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert hasattr(module, "asyncio"), f"{module_name} must import asyncio"
        assert hasattr(module.asyncio, "sleep"), f"{module_name} asyncio import is invalid"


def test_registered_workers_and_queue_definitions_match() -> None:
    factory = WorkerFactory()

    queue_worker_types = {queue.worker_type for queue in get_all_queue_configs()}
    registered_worker_types = set(factory.get_supported_worker_types())

    assert queue_worker_types == registered_worker_types

    for queue in get_all_queue_configs():
        worker = factory.create_worker(queue.worker_type, queue.name)
        assert worker.queue_config.name == queue.name
        assert factory.get_queue_config(queue.name) is not None
