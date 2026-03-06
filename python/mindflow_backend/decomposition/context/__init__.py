"""Semantic context sharing between sub-tasks.

Re-exports the production-ready SemanticContextManager from
``orchestrator.semantic_context_manager``.  The import is intentionally
deferred to avoid loading ``sentence_transformers`` at package import time.
"""

from __future__ import annotations


def get_semantic_context_manager():  # type: ignore[return]
    """Lazy proxy — delegates to the orchestrator implementation."""
    from mindflow_backend.orchestrator.semantic_context_manager import (  # noqa: PLC0415
        get_semantic_context_manager as _get,
    )
    return _get()


__all__ = ["get_semantic_context_manager"]
