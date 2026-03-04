from datetime import UTC, datetime

import orjson

from omnimind_backend.infra.redis import get_async_redis
from omnimind_backend.schemas.chat.agent import LogEntry, StreamEvent


class AgentLogBus:
    HISTORY_STREAM_KEY = "omnimind:agent:logs"

    async def publish(self, event: StreamEvent, turn_id: str) -> None:
        redis = get_async_redis()
        entry = LogEntry(
            **event.model_dump(),
            turnId=turn_id,
            wallTime=datetime.now(UTC).isoformat(),
        )
        payload = orjson.dumps(entry.model_dump()).decode("utf-8")
        await redis.xadd(self.HISTORY_STREAM_KEY, {"data": payload}, maxlen=500, approximate=True)

    async def get_recent(self, limit: int = 500) -> list[LogEntry]:
        redis = get_async_redis()
        rows = await redis.xrevrange(self.HISTORY_STREAM_KEY, count=limit)
        items: list[LogEntry] = []
        for _, fields in reversed(rows):
            raw = fields.get("data")
            if not raw:
                continue
            try:
                items.append(LogEntry.model_validate_json(raw))
            except Exception:
                continue
        return items


log_bus = AgentLogBus()
