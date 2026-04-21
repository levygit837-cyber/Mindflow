"""Hierarchical RabbitMQ workers for MindFlow."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AgentTask",
    "AgentTaskDefinitions",
    "AnalystWorker",
    "BaseWorker",
    "CoderWorker",
    "HealthWorker",
    "MemoryWorker",
    "OrchestratorWorker",
    "QueueConfig",
    "QueueManager",
    "ResearchTask",
    "ResearchTaskDefinitions",
    "ResearcherWorker",
    "SystemTask",
    "SystemTaskDefinitions",
    "VectorWorker",
    "WorkerConfigurationError",
    "WorkerConnectionError",
    "WorkerError",
    "WorkerFactory",
    "WorkerMonitor",
    "WorkerProcessingError",
    "WorkerResult",
    "WorkerSettings",
    "WorkerStatus",
    "get_agent_task_publisher",
    "get_queue_config",
    "get_research_task_publisher",
    "get_system_task_publisher",
    "get_worker_settings",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "AnalystWorker": ("mindflow_backend.workers.agents", "AnalystWorker"),
    "CoderWorker": ("mindflow_backend.workers.agents", "CoderWorker"),
    "OrchestratorWorker": ("mindflow_backend.workers.agents", "OrchestratorWorker"),
    "ResearcherWorker": ("mindflow_backend.workers.agents", "ResearcherWorker"),
    "BaseWorker": ("mindflow_backend.workers.base", "BaseWorker"),
    "WorkerConfigurationError": (
        "mindflow_backend.workers.base",
        "WorkerConfigurationError",
    ),
    "WorkerConnectionError": ("mindflow_backend.workers.base", "WorkerConnectionError"),
    "WorkerError": ("mindflow_backend.workers.base", "WorkerError"),
    "WorkerProcessingError": ("mindflow_backend.workers.base", "WorkerProcessingError"),
    "WorkerResult": ("mindflow_backend.workers.base", "WorkerResult"),
    "WorkerStatus": ("mindflow_backend.workers.base", "WorkerStatus"),
    "QueueConfig": ("mindflow_backend.workers.config", "QueueConfig"),
    "WorkerSettings": ("mindflow_backend.workers.config", "WorkerSettings"),
    "get_queue_config": ("mindflow_backend.workers.config", "get_queue_config"),
    "get_worker_settings": ("mindflow_backend.workers.config", "get_worker_settings"),
    "QueueManager": ("mindflow_backend.workers.infrastructure", "QueueManager"),
    "WorkerFactory": ("mindflow_backend.workers.infrastructure", "WorkerFactory"),
    "WorkerMonitor": ("mindflow_backend.workers.infrastructure", "WorkerMonitor"),
    "HealthWorker": ("mindflow_backend.workers.system", "HealthWorker"),
    "MemoryWorker": ("mindflow_backend.workers.system", "MemoryWorker"),
    "VectorWorker": ("mindflow_backend.workers.system", "VectorWorker"),
    "AgentTaskDefinitions": ("mindflow_backend.workers.tasks", "AgentTaskDefinitions"),
    "ResearchTaskDefinitions": ("mindflow_backend.workers.tasks", "ResearchTaskDefinitions"),
    "SystemTaskDefinitions": ("mindflow_backend.workers.tasks", "SystemTaskDefinitions"),
    "AgentTask": ("mindflow_backend.workers.tasks.agent_tasks", "AgentTask"),
    "get_agent_task_publisher": (
        "mindflow_backend.workers.tasks.agent_tasks",
        "get_agent_task_publisher",
    ),
    "ResearchTask": ("mindflow_backend.workers.tasks.research_tasks", "ResearchTask"),
    "get_research_task_publisher": (
        "mindflow_backend.workers.tasks.research_tasks",
        "get_research_task_publisher",
    ),
    "SystemTask": ("mindflow_backend.workers.tasks.system_tasks", "SystemTask"),
    "get_system_task_publisher": (
        "mindflow_backend.workers.tasks.system_tasks",
        "get_system_task_publisher",
    ),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _LAZY_ATTRS[name]
    except KeyError as exc:  # pragma: no cover - Python fallback path
        raise AttributeError(name) from exc
    module = import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
