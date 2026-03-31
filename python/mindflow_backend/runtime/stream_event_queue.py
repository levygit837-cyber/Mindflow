"""Compatibility re-export for StreamEventQueue.

Historically `AgentChatStreamNormalizer` imported `StreamEventQueue` from
`mindflow_backend.runtime.stream_event_queue`, while the implementation lives
under `mindflow_backend.runtime.streaming.stream_event_queue`.
"""

from __future__ import annotations

from mindflow_backend.runtime.streaming.stream_event_queue import (  # noqa: F401
    QueuedEvent,
    StreamEventQueue,
)

__all__ = ["StreamEventQueue", "QueuedEvent"]

