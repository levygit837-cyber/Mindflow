"""Context retrieval system for MindFlow agents."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AgentContextRetriever",
    "ContextCache",
    "InMemoryVectorStore",
    "SessionContentAnalyzer",
    "get_agent_context_retriever",
    "get_content_analyzer",
    "get_context_cache",
    "get_vector_store",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "SessionContentAnalyzer": (
        "mindflow_backend.agents.context.analyzer",
        "SessionContentAnalyzer",
    ),
    "get_content_analyzer": (
        "mindflow_backend.agents.context.analyzer",
        "get_content_analyzer",
    ),
    "ContextCache": ("mindflow_backend.agents.context.cache", "ContextCache"),
    "get_context_cache": ("mindflow_backend.agents.context.cache", "get_context_cache"),
    "AgentContextRetriever": (
        "mindflow_backend.agents.context.retriever",
        "AgentContextRetriever",
    ),
    "get_agent_context_retriever": (
        "mindflow_backend.agents.context.retriever",
        "get_agent_context_retriever",
    ),
    "InMemoryVectorStore": (
        "mindflow_backend.agents.context.vector_store",
        "InMemoryVectorStore",
    ),
    "get_vector_store": ("mindflow_backend.agents.context.vector_store", "get_vector_store"),
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
