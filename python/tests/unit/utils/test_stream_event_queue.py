from mindflow_backend.runtime.streaming.stream_event_queue import StreamEventQueue
from mindflow_backend.schemas.agent import StreamEventMeta


def test_insert_before_marker_on_drain() -> None:
    queue = StreamEventQueue()
    marker = queue.set_first_response_marker("run-1")
    assert marker == "first-response-run-1"

    queue.enqueue(
        event_type="tool_call",
        data="{}",
        mode="updates",
        meta=StreamEventMeta(),
        wants_insert_before=True,
    )

    drained = queue.drain()
    assert len(drained) == 1
    assert drained[0].meta is not None
    assert drained[0].meta.insertBefore == "first-response-run-1"
