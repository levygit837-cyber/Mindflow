# Streaming runtime utilities
# Decomposed from AgentRuntime in stream.py

from __future__ import annotations

from .context_builder import _build_context_bundle, _snapshot_json
from .decision_handler import (
    _decision_agent_task,
    _decision_payload,
    _is_direct_response,
    _serialize_decision,
)
from .event_processor import (
    _next_seq,
    _resolve_execution_mode,
    _resolve_memory_agent_id,
    _should_force_structured_analyst_flow,
)
from .history_loader import _HISTORY_WINDOW, _load_history_messages
from .watchdog import _counts_as_tool_watchdog_progress, _counts_as_watchdog_progress

__all__ = [
    # Context builder
    "_build_context_bundle",
    "_snapshot_json",
    # Decision handler
    "_is_direct_response",
    "_serialize_decision",
    "_decision_payload",
    "_decision_agent_task",
    # Event processor
    "_next_seq",
    "_resolve_execution_mode",
    "_should_force_structured_analyst_flow",
    "_resolve_memory_agent_id",
    # History loader
    "_load_history_messages",
    "_HISTORY_WINDOW",
    # Watchdog
    "_counts_as_watchdog_progress",
    "_counts_as_tool_watchdog_progress",
]
