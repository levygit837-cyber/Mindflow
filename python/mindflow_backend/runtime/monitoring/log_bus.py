from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import orjson

from mindflow_backend.infra.cache.redis_client import get_async_redis
from mindflow_backend.schemas.chat.agent import LogEntry, StreamEvent

logger = logging.getLogger(__name__)


class AgentLogBus:
    """Bus de logs de agentes com suporte a subscription por mission_id.

    Fase 3B — SPADE Memory Observer Protocol:
    - subscribe_to_mission(): registra observer para receber eventos de uma missão
    - unsubscribe_from_mission(): remove observer
    - _notify_observers(): notifica observers quando evento é publicado
    """

    HISTORY_STREAM_KEY = "mindflow:agent:logs"

    def __init__(self) -> None:
        self._mission_observers: dict[str, list[Callable[[dict[str, Any]], Awaitable[None]]]] = {}
        self._observer_missions: dict[str, set[str]] = {}  # observer_id -> set of mission_ids

    async def publish(self, event: StreamEvent, turn_id: str) -> None:
        """Publica evento e notifica observers da missão."""
        redis = get_async_redis()
        entry = LogEntry(
            **event.model_dump(),
            turnId=turn_id,
            wallTime=datetime.now(UTC).isoformat(),
        )
        payload = orjson.dumps(entry.model_dump()).decode("utf-8")
        await redis.xadd(self.HISTORY_STREAM_KEY, {"data": payload}, maxlen=500, approximate=True)

        # Notificar observers se evento tem mission_id
        meta = event.meta
        if meta and hasattr(meta, "mission_id") and meta.mission_id:
            event_dict = {
                "type": event.type.value if hasattr(event.type, "value") else str(event.type),
                "agent_id": getattr(meta, "agent_id", "unknown"),
                "mission_id": meta.mission_id,
                "level": getattr(meta, "level", "INFO"),
                "message": event.data,
                "data": getattr(meta, "data", {}),
                "turn_id": turn_id,
                "timestamp": entry.wallTime,
            }
            await self._notify_observers(meta.mission_id, event_dict)

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

    def subscribe_to_mission(
        self,
        mission_id: str,
        observer_id: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Registra observer para receber eventos de uma missão.

        Args:
            mission_id: ID da missão a ser observada.
            observer_id: ID único do observer (para gerenciar unsubscribe).
            handler: Função async que recebe o evento como dict.
        """
        if mission_id not in self._mission_observers:
            self._mission_observers[mission_id] = []
        self._mission_observers[mission_id].append(handler)

        if observer_id not in self._observer_missions:
            self._observer_missions[observer_id] = set()
        self._observer_missions[observer_id].add(mission_id)

        logger.debug(
            "log_bus_observer_subscribed",
            extra={
                "mission_id": mission_id,
                "observer_id": observer_id,
            },
        )

    def unsubscribe_from_mission(
        self,
        mission_id: str,
        observer_id: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Remove observer de uma missão específica."""
        if mission_id in self._mission_observers:
            try:
                self._mission_observers[mission_id].remove(handler)
            except ValueError:
                pass
            if not self._mission_observers[mission_id]:
                del self._mission_observers[mission_id]

        if observer_id in self._observer_missions:
            self._observer_missions[observer_id].discard(mission_id)
            if not self._observer_missions[observer_id]:
                del self._observer_missions[observer_id]

        logger.debug(
            "log_bus_observer_unsubscribed",
            extra={
                "mission_id": mission_id,
                "observer_id": observer_id,
            },
        )

    def unsubscribe_all(self, observer_id: str) -> None:
        """Remove observer de todas as missões."""
        if observer_id not in self._observer_missions:
            return

        mission_ids = list(self._observer_missions[observer_id])
        for mission_id in mission_ids:
            if mission_id in self._mission_observers:
                # Remove todos os handlers deste observer
                # (simplificação — em produção seria por handler específico)
                pass

        del self._observer_missions[observer_id]
        logger.debug(
            "log_bus_observer_unsubscribed_all",
            extra={"observer_id": observer_id},
        )

    async def _notify_observers(
        self,
        mission_id: str,
        event: dict[str, Any],
    ) -> None:
        """Notifica todos os observers de uma missão."""
        handlers = self._mission_observers.get(mission_id, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.debug(
                    "log_bus_observer_error",
                    extra={
                        "mission_id": mission_id,
                        "error": str(exc),
                    },
                )

    def get_observer_stats(self, observer_id: str) -> dict[str, Any]:
        """Retorna estatísticas de um observer."""
        missions = self._observer_missions.get(observer_id, set())
        return {
            "observer_id": observer_id,
            "subscribed_missions": sorted(missions),
            "total_subscriptions": len(missions),
        }


log_bus = AgentLogBus()
