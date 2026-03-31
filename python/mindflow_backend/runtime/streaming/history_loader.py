# History loading utilities for streaming runtime
# Extracted from AgentRuntime in stream.py

from __future__ import annotations

from typing import Any

_HISTORY_WINDOW = 50


async def _load_history_messages(session_id: str, limit: int = _HISTORY_WINDOW) -> list[Any]:
    """Load recent messages for a session.
    
    Returns a list of message dicts suitable for passing to the
    orchestrator graph as the initial ``messages`` state.
    """
    from mindflow_backend.memory.session_memory.service import get_session_memory_service

    memory_service = get_session_memory_service()
    if not memory_service:
        return []
    
    try:
        messages = await memory_service.get_recent_messages(session_id, limit=limit)
        return messages or []
    except Exception:
        return []


__all__ = ["_load_history_messages", "_HISTORY_WINDOW"]