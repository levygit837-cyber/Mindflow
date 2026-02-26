from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .types import StreamEventType, StreamModeName

EmitFn = Callable[[StreamEventType, str, StreamModeName, Dict[str, Any]], None]


@dataclass
class QueuedEvent:
    type: StreamEventType
    data: str
    mode: StreamModeName
    meta: Dict[str, Any]
    wants_insert_before: bool


class StreamEventQueue:
    def __init__(self) -> None:
        self.queue: List[QueuedEvent] = []
        self.first_response_marker: Optional[str] = None

    def set_first_response_marker(self, turn_run_id: str) -> str:
        if not self.first_response_marker:
            self.first_response_marker = f"first-response-{turn_run_id}"
        return self.first_response_marker

    def has_first_response_marker(self) -> bool:
        return self.first_response_marker is not None

    def enqueue(
        self,
        event_type: StreamEventType,
        data: str,
        mode: StreamModeName,
        meta: Dict[str, Any],
        wants_insert_before: bool,
    ) -> None:
        self.queue.append(QueuedEvent(event_type, data, mode, meta, wants_insert_before))

    def drain(self, emit: EmitFn) -> None:
        for item in self.queue:
            final_meta = dict(item.meta)
            if item.wants_insert_before and self.first_response_marker:
                final_meta["insertBefore"] = self.first_response_marker
            emit(item.type, item.data, item.mode, final_meta)
        self.queue = []

    def reset(self) -> None:
        self.queue = []
        self.first_response_marker = None
