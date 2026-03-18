"""Planning module for intelligent TODO-list triggering and analysis."""

from __future__ import annotations

__all__ = ["get_planning_analyzer"]


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "get_planning_analyzer":
        from mindflow_backend.orchestrator.planning.analyzer import get_planning_analyzer
        return get_planning_analyzer
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
