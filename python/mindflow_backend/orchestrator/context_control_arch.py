"""Shim — re-exports from orchestrator.context.control (lazy to avoid circular import)."""
from __future__ import annotations

from typing import TYPE_CHECKING


def __getattr__(name: str):
    """Lazy import to break circular dependency with context.budget."""
    import importlib
    _mod = importlib.import_module("mindflow_backend.orchestrator.context.control")
    if hasattr(_mod, name):
        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Keep explicit re-exports for static analysis / IDE support
if TYPE_CHECKING:
    from mindflow_backend.orchestrator.context.control import (  # noqa: F401
        context_control_arch,
        get_window_position,
        get_window_bounds,
        is_window_boundary_crossed,
        calculate_session_hierarchy,
    )
