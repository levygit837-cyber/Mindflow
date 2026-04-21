from __future__ import annotations

from mindflow_backend.workers.agents.researcher_worker import ResearcherWorker
from mindflow_backend.workers.infrastructure.worker_factory import WorkerFactory


def test_worker_factory_registers_browser_and_content_workers() -> None:
    factory = WorkerFactory()

    assert "browser" in factory.get_supported_worker_types()
    assert "content" in factory.get_supported_worker_types()

    browser_worker = factory.create_worker("browser")
    content_worker = factory.create_worker("content")

    assert isinstance(browser_worker, ResearcherWorker)
    assert browser_worker.queue_config.name == "browser_high"
    assert isinstance(content_worker, ResearcherWorker)
    assert content_worker.queue_config.name == "content_medium"
