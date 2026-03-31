"""Shim — re-exports from orchestrator.context.semantic for backward compatibility."""

from mindflow_backend.orchestrator.context.semantic import (
    ContextEntry,
    ContextMatch,
    SemanticContextManager,
    get_semantic_context_manager,
)

__all__ = [
    "ContextMatch",
    "ContextEntry",
    "SemanticContextManager",
    "get_semantic_context_manager",
]
