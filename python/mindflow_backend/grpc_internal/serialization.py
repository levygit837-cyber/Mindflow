"""Utilities for serializing MindFlow domain objects to/from protobuf messages."""

from __future__ import annotations

import json
from typing import Any

from mindflow_backend.schemas.chat.agent import StreamEvent


def stream_event_to_proto(event: StreamEvent, pb2: Any) -> Any:
    """Convert a domain StreamEvent to a pb2.StreamEvent protobuf message.

    Args:
        event: The domain StreamEvent to convert.
        pb2: The generated protobuf module (mindflow_backend_pb2).

    Returns:
        A pb2.StreamEvent protobuf message.
    """
    json_meta = ""
    if event.meta is not None:
        try:
            if hasattr(event.meta, "model_dump"):
                json_meta = json.dumps(event.meta.model_dump())
            elif isinstance(event.meta, dict):
                json_meta = json.dumps(event.meta)
            else:
                json_meta = json.dumps(dict(event.meta))
        except Exception:
            json_meta = "{}"

    return pb2.StreamEvent(
        id=event.id or "",
        seq=event.seq or 0,
        type=event.type or "",
        mode=event.mode or "",
        data=event.data or "",
        json_meta=json_meta,
    )
