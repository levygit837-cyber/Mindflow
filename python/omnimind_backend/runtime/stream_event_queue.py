from dataclasses import dataclass

from omnimind_backend.schemas.agent import StreamEventMeta, StreamEventType, StreamModeName


@dataclass
class QueuedEvent:
    event_type: StreamEventType
    data: str
    mode: StreamModeName
    meta: StreamEventMeta | None
    wants_insert_before: bool


class StreamEventQueue:
    def __init__(self) -> None:
        self._queue: list[QueuedEvent] = []
        self._first_response_marker: str | None = None

    def set_first_response_marker(self, turn_run_id: str) -> str:
        if self._first_response_marker is None:
            self._first_response_marker = f"first-response-{turn_run_id}"
        return self._first_response_marker

    def has_first_response_marker(self) -> bool:
        return self._first_response_marker is not None

    def enqueue(
        self,
        event_type: StreamEventType,
        data: str,
        mode: StreamModeName,
        meta: StreamEventMeta | None,
        wants_insert_before: bool,
    ) -> None:
        self._queue.append(
            QueuedEvent(
                event_type=event_type,
                data=data,
                mode=mode,
                meta=meta,
                wants_insert_before=wants_insert_before,
            )
        )

    def drain(self) -> list[QueuedEvent]:
        drained: list[QueuedEvent] = []
        for item in self._queue:
            if item.wants_insert_before and self._first_response_marker is not None:
                meta = item.meta or StreamEventMeta()
                meta.insertBefore = self._first_response_marker
                item.meta = meta
            drained.append(item)
        self._queue = []
        return drained

    def reset(self) -> None:
        self._queue = []
        self._first_response_marker = None
