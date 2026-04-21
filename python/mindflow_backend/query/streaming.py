"""Stream-event building helpers for the unified QueryEngine kernel.

Pure functions (no class, no ``self``) that build typed ``StreamEvent``
objects. Previously these were private methods on ``AgentRuntime`` in
``runtime/streaming/stream.py``.

The ``seq_counter`` convention (a ``list[int]`` to allow mutation in-place)
is preserved for backward-compatibility with the normalizer's contract.
Callers that don't care about ordering can pass ``[0]`` and ignore the
return value.

Phase 2 of the unified-engine plan — see
.windsurf/plans/unified-engine-47796c.md §4.2.
"""

from __future__ import annotations

from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta


def next_seq(counter: list[int]) -> int:
    """Increment ``counter[0]`` in place and return the new value."""
    counter[0] += 1
    return counter[0]


def error_event(
    *,
    exc: Exception,
    counter: list[int],
    provider: str,
    model: str,
    run_id: str,
    session_id: str,
    node: str = "unknown",
    node_category: str = "RUNTIME",
) -> StreamEvent:
    """Build a typed ``error`` StreamEvent."""
    seq = next_seq(counter)
    return StreamEvent(
        id=f"evt-{seq}",
        seq=seq,
        type="error",
        mode="custom",
        data=str(exc),
        meta=StreamEventMeta(
            provider=provider,
            model=model,
            runId=run_id,
            turnRunId=session_id,
            node=node,
            nodeCategory=node_category,
            userVisible=True,
        ),
    )


def done_event(
    *,
    counter: list[int],
    provider: str,
    model: str,
    run_id: str,
    session_id: str,
) -> StreamEvent:
    """Build the terminal ``done`` StreamEvent."""
    seq = next_seq(counter)
    return StreamEvent(
        id=f"evt-{seq}",
        seq=seq,
        type="done",
        mode="messages",
        data="",
        meta=StreamEventMeta(
            provider=provider,
            model=model,
            runId=run_id,
            turnRunId=session_id,
        ),
    )


def custom_event(
    *,
    counter: list[int],
    run_id: str,
    session_id: str,
    event_type: str,
    data: str = "",
    agent: str | None = None,
    node: str = "orchestrator",
    node_category: str = "RUNTIME",
) -> StreamEvent:
    """Build a custom ``StreamEvent`` (``orchestrator_*``, ``reflection_*``, etc.)."""
    seq = next_seq(counter)
    meta = StreamEventMeta(
        runId=run_id,
        turnRunId=session_id,
        node=node,
        nodeCategory=node_category,
        userVisible=True,
    )
    if agent:
        meta.agent = agent
    return StreamEvent(
        id=f"evt-{seq}",
        seq=seq,
        type=event_type,  # type: ignore[arg-type]
        mode="custom",
        data=data,
        meta=meta,
    )
