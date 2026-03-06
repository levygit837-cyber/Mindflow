import json
from typing import Any


def format_sse(data: Any, event_id: str | int | None = None) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=True)
    if event_id is None:
        return f"data: {payload}\n\n"
    return f"id: {event_id}\ndata: {payload}\n\n"
