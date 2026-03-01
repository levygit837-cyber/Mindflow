"""Backward-compatible shim — canonical location: omnimind_backend.runtime.stream_event_queue"""

from omnimind_backend.runtime.stream_event_queue import (  # noqa: F401
    QueuedEvent,
    StreamEventQueue,
)

__all__ = ["QueuedEvent", "StreamEventQueue"]
