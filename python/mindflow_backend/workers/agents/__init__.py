"""Agent workers module."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AnalystWorker",
    "CoderWorker",
    "OrchestratorWorker",
    "ResearcherWorker",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "AnalystWorker": ("mindflow_backend.workers.agents.analyst_worker", "AnalystWorker"),
    "CoderWorker": ("mindflow_backend.workers.agents.coder_worker", "CoderWorker"),
    "OrchestratorWorker": (
        "mindflow_backend.workers.agents.orchestrator_worker",
        "OrchestratorWorker",
    ),
    "ResearcherWorker": (
        "mindflow_backend.workers.agents.researcher_worker",
        "ResearcherWorker",
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
