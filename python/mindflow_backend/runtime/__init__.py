"""Streaming infrastructure and execution runtime.

Expose the public runtime surface lazily to avoid circular imports between the
runtime shell, monitoring, and service packages.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AgentLogBus",
    "AgentChatStreamNormalizer",
    "BackendProtocol",
    "ExecuteResult",
    "MemoryIntegration",
    "NodeCategory",
    "OutputCategory",
    "QueuedEvent",
    "RuntimeAgentRuntime",
    "RuntimeRouter",
    "SafeBackend",
    "StreamEventQueue",
    "StreamManager",
    "categorize_output",
    "classify_node",
    "extract_ai_message_content",
    "extract_text_only",
    "extract_thinking_only",
    "get_model_for_provider",
    "get_node_label",
    "has_thinking_content",
    "is_streamable_node",
    "log_bus",
    "normalize_response_for_json",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "RuntimeAgentRuntime": ("mindflow_backend.runtime.streaming.stream", "AgentRuntime"),
    "BackendProtocol": ("mindflow_backend.runtime.execution.safe_backend", "BackendProtocol"),
    "ExecuteResult": ("mindflow_backend.runtime.execution.safe_backend", "ExecuteResult"),
    "SafeBackend": ("mindflow_backend.runtime.execution.safe_backend", "SafeBackend"),
    "MemoryIntegration": ("mindflow_backend.runtime.memory.memory_integration", "MemoryIntegration"),
    "OutputCategory": (
        "mindflow_backend.runtime.processing.output_categorizer",
        "OutputCategory",
    ),
    "categorize_output": (
        "mindflow_backend.runtime.processing.output_categorizer",
        "categorize_output",
    ),
    "get_model_for_provider": (
        "mindflow_backend.runtime.providers.providers",
        "get_model_for_provider",
    ),
    "NodeCategory": ("mindflow_backend.runtime.registry.node_registry", "NodeCategory"),
    "classify_node": ("mindflow_backend.runtime.registry.node_registry", "classify_node"),
    "get_node_label": ("mindflow_backend.runtime.registry.node_registry", "get_node_label"),
    "is_streamable_node": (
        "mindflow_backend.runtime.registry.node_registry",
        "is_streamable_node",
    ),
    "RuntimeRouter": ("mindflow_backend.runtime.routing.runtime_router", "RuntimeRouter"),
    "AgentChatStreamNormalizer": (
        "mindflow_backend.runtime.streaming.normalizer",
        "AgentChatStreamNormalizer",
    ),
    "QueuedEvent": (
        "mindflow_backend.runtime.streaming.stream_event_queue",
        "QueuedEvent",
    ),
    "StreamEventQueue": (
        "mindflow_backend.runtime.streaming.stream_event_queue",
        "StreamEventQueue",
    ),
    "StreamManager": ("mindflow_backend.runtime.streaming.stream_manager", "StreamManager"),
    "extract_ai_message_content": (
        "mindflow_backend.runtime.utils.response_parser",
        "extract_ai_message_content",
    ),
    "extract_text_only": (
        "mindflow_backend.runtime.utils.response_parser",
        "extract_text_only",
    ),
    "extract_thinking_only": (
        "mindflow_backend.runtime.utils.response_parser",
        "extract_thinking_only",
    ),
    "has_thinking_content": (
        "mindflow_backend.runtime.utils.response_parser",
        "has_thinking_content",
    ),
    "normalize_response_for_json": (
        "mindflow_backend.runtime.utils.response_parser",
        "normalize_response_for_json",
    ),
    "AgentLogBus": ("mindflow_backend.runtime.monitoring.log_bus", "AgentLogBus"),
    "log_bus": ("mindflow_backend.runtime.monitoring.log_bus", "log_bus"),
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
