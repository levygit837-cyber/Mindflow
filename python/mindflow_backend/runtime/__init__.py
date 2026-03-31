"""Streaming infrastructure and execution runtime."""

from mindflow_backend.runtime.core.agent_runtime import AgentRuntime as RuntimeAgentRuntime
from mindflow_backend.runtime.execution.executor import RuntimeExecutor
from mindflow_backend.runtime.execution.safe_backend import (
    BackendProtocol,
    ExecuteResult,
    SafeBackend,
)
from mindflow_backend.runtime.memory.memory_integration import MemoryIntegration
from mindflow_backend.runtime.monitoring.log_bus import AgentLogBus, log_bus
from mindflow_backend.runtime.processing.output_categorizer import OutputCategory, categorize_output
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.runtime.registry.node_registry import (
    NodeCategory,
    classify_node,
    get_node_label,
    is_streamable_node,
)
from mindflow_backend.runtime.routing.runtime_router import RuntimeRouter
from mindflow_backend.runtime.streaming.normalizer import AgentChatStreamNormalizer
from mindflow_backend.runtime.streaming.stream_event_queue import (
    QueuedEvent,
    StreamEventQueue,
)
from mindflow_backend.runtime.streaming.stream_manager import StreamManager
from mindflow_backend.runtime.utils.response_parser import (
    extract_ai_message_content,
    extract_text_only,
    extract_thinking_only,
    has_thinking_content,
    normalize_response_for_json,
)

__all__ = [
    # Modular runtime (new)
    "RuntimeAgentRuntime",
    "RuntimeRouter",
    "RuntimeExecutor",
    "MemoryIntegration",
    "StreamManager",
    # Existing exports
    "AgentChatStreamNormalizer",
    "AgentLogBus",
    "BackendProtocol",
    "ExecuteResult",
    "NodeCategory",
    "OutputCategory",
    "QueuedEvent",
    "SafeBackend",
    "StreamEventQueue",
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
