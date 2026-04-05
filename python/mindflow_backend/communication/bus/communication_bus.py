"""CommunicationBus — Camada de transporte unificada para mensagens entre agentes.

Abstract base + InternalCommunicationBus (asyncio queues, zero infra externa).
XMPPCommunicationBus será implementado na Fase 4.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from mindflow_backend.communication.protocols.p2p_protocol import (
    MessageType,
    P2PMessage,
)
from mindflow_backend.communication.teams.team_chat import TeamMessage
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.resilience.circuit_breaker.core import CircuitBreaker
from mindflow_backend.infra.resilience.orchestration_fallback import (
    FallbackContext,
    get_orchestration_fallback_manager,
)

logger = get_logger(__name__)


class CommunicationBus(ABC):
    """Camada de transporte abstrata para mensagens entre agentes.

    Permite trocar InternalBus por XMPPBus sem alterar código dos agentes.
    """

    @abstractmethod
    async def register_agent(self, agent_id: str) -> None:
        """Registra um agente no bus (cria sua inbox)."""

    @abstractmethod
    async def unregister_agent(self, agent_id: str) -> None:
        """Remove agente do bus."""

    @abstractmethod
    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message: P2PMessage,
    ) -> bool:
        """Envia mensagem P2P. Retorna True se entregue."""

    @abstractmethod
    async def broadcast(
        self,
        from_agent: str,
        room_id: str,
        message: TeamMessage,
    ) -> bool:
        """Envia mensagem para room MUC. Retorna True se entregue."""

    @abstractmethod
    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[P2PMessage], Awaitable[None]],
    ) -> None:
        """Registra handler assíncrono para mensagens recebidas pelo agente."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Retorna status do bus."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True se o bus está operacional."""


class InternalCommunicationBus(CommunicationBus):
    """CommunicationBus baseado em asyncio.Queue — zero dependência externa.

    Cada agente tem sua própria inbox (Queue).
    Mensagens têm TTL de 30s para evitar acúmulo.
    """

    TTL_SECONDS: float = 30.0
    MAX_QUEUE_SIZE: int = 100

    def __init__(self) -> None:
        self._inboxes: dict[str, asyncio.Queue[P2PMessage]] = {}
        self._room_subscribers: dict[str, list[str]] = {}
        self._handlers: dict[str, list[Callable]] = {}
        self._running = True
        self._circuit_breaker = CircuitBreaker(
            name="internal_bus",
        )
        self._stats = {
            "messages_sent": 0,
            "messages_dropped": 0,
            "agents_registered": 0,
        }
        self.settings = get_settings()
        self._fallback_manager = get_orchestration_fallback_manager()
        self._register_fallback_handlers()

    def _register_fallback_handlers(self) -> None:
        """Register fallback handlers for communication bus."""

        async def send_fallback(ctx: FallbackContext) -> bool:
            """Fallback handler for send - return False (message not delivered)."""
            logger.warning(
                "communication_bus_send_fallback",
                original_error=str(ctx.original_error),
            )
            return False

        async def broadcast_fallback(ctx: FallbackContext) -> bool:
            """Fallback handler for broadcast - return False (message not delivered)."""
            logger.warning(
                "communication_bus_broadcast_fallback",
                original_error=str(ctx.original_error),
            )
            return False

        self._fallback_manager.register_fallback_handler("communication_bus_send", send_fallback)
        self._fallback_manager.register_fallback_handler("communication_bus_broadcast", broadcast_fallback)

    async def register_agent(self, agent_id: str) -> None:
        if agent_id not in self._inboxes:
            self._inboxes[agent_id] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
            self._handlers[agent_id] = []
            self._stats["agents_registered"] += 1
            logger.info("bus_agent_registered", extra={"agent_id": agent_id})

    async def unregister_agent(self, agent_id: str) -> None:
        self._inboxes.pop(agent_id, None)
        self._handlers.pop(agent_id, None)
        logger.info("bus_agent_unregistered", extra={"agent_id": agent_id})

    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message: P2PMessage,
    ) -> bool:
        async def _do_send() -> bool:
            inbox = self._inboxes.get(to_agent)
            if inbox is None:
                logger.warning(
                    "bus_send_no_inbox",
                    extra={"from": from_agent, "to": to_agent},
                )
                self._stats["messages_dropped"] += 1
                return False

            try:
                inbox.put_nowait(message)
                self._stats["messages_sent"] += 1
                logger.debug(
                    "bus_message_sent",
                    extra={
                        "from": from_agent,
                        "to": to_agent,
                        "msg_id": message.message_id,
                    },
                )
                await self._dispatch_handlers(to_agent, message)
                return True
            except asyncio.QueueFull:
                logger.warning(
                    "bus_queue_full",
                    extra={"agent_id": to_agent},
                )
                self._stats["messages_dropped"] += 1
                return False

        # Execute with fallback (includes retry logic automatically)
        if self.settings.orchestration_fallback.communication_bus_enabled:
            async def _send_with_circuit_breaker() -> bool:
                return await self._circuit_breaker.execute(_do_send)

            fallback_result = await self._fallback_manager.execute_with_fallback(
                component="communication_bus_send",
                primary_func=_send_with_circuit_breaker,
                context={"from_agent": from_agent, "to_agent": to_agent},
            )
            if fallback_result.success:
                return fallback_result.result
            else:
                logger.warning(
                    "bus_circuit_open",
                    extra={"from": from_agent, "to": to_agent},
                )
                self._stats["messages_dropped"] += 1
                return False
        else:
            # Use only circuit breaker without orchestration fallback
            try:
                return await self._circuit_breaker.execute(_do_send)
            except Exception:
                logger.warning(
                    "bus_circuit_open",
                    extra={"from": from_agent, "to": to_agent},
                )
                self._stats["messages_dropped"] += 1
                return False

    async def broadcast(
        self,
        from_agent: str,
        room_id: str,
        message: TeamMessage,
    ) -> bool:
        async def _do_broadcast() -> bool:
            subscribers = self._room_subscribers.get(room_id, [])
            if not subscribers:
                logger.warning("bus_broadcast_no_subscribers", extra={"room_id": room_id})
                return False

            delivered = 0
            for agent_id in subscribers:
                if agent_id == from_agent:
                    continue
                p2p_msg = P2PMessage(
                    from_agent=from_agent,
                    to_agent=agent_id,
                    content=message.content,
                    message_type=MessageType.DIRECT,
                    metadata={"room_id": room_id, "team_message_id": message.message_id},
                )
                if await self.send(from_agent, agent_id, p2p_msg):
                    delivered += 1

            return delivered > 0

        # Execute with fallback (includes retry logic automatically)
        if self.settings.orchestration_fallback.communication_bus_enabled:
            fallback_result = await self._fallback_manager.execute_with_fallback(
                component="communication_bus_broadcast",
                primary_func=_do_broadcast,
                context={"from_agent": from_agent, "room_id": room_id},
            )
            if fallback_result.success:
                return fallback_result.result
            else:
                logger.warning(
                    "bus_broadcast_failed",
                    extra={"from": from_agent, "room_id": room_id},
                )
                return False
        else:
            return await _do_broadcast()

    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[P2PMessage], Awaitable[None]],
    ) -> None:
        if agent_id not in self._handlers:
            self._handlers[agent_id] = []
        self._handlers[agent_id].append(handler)

    def join_room(self, agent_id: str, room_id: str) -> None:
        """Adiciona agente a um room MUC (para broadcast)."""
        if room_id not in self._room_subscribers:
            self._room_subscribers[room_id] = []
        if agent_id not in self._room_subscribers[room_id]:
            self._room_subscribers[room_id].append(agent_id)

    def leave_room(self, agent_id: str, room_id: str) -> None:
        """Remove agente de um room MUC."""
        if room_id in self._room_subscribers:
            self._room_subscribers[room_id] = [
                a for a in self._room_subscribers[room_id] if a != agent_id
            ]

    async def receive(
        self,
        agent_id: str,
        timeout: float = 1.0,
    ) -> P2PMessage | None:
        """Recebe próxima mensagem da inbox do agente (non-blocking com timeout)."""
        inbox = self._inboxes.get(agent_id)
        if inbox is None:
            return None
        try:
            return await asyncio.wait_for(inbox.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def health_check(self) -> dict[str, Any]:
        return {
            "type": "internal",
            "available": self._running,
            "agents": list(self._inboxes.keys()),
            "rooms": {
                room_id: len(subs)
                for room_id, subs in self._room_subscribers.items()
            },
            "stats": self._stats.copy(),
            "circuit_breaker": self._circuit_breaker.get_stats(),
        }

    @property
    def is_available(self) -> bool:
        return self._running

    async def _dispatch_handlers(
        self,
        agent_id: str,
        message: P2PMessage,
    ) -> None:
        for handler in self._handlers.get(agent_id, []):
            try:
                await handler(message)
            except Exception as exc:
                logger.error(
                    "bus_handler_error",
                    extra={"agent_id": agent_id, "error": str(exc)},
                )


# Singleton global
_global_bus: CommunicationBus | None = None


def get_communication_bus() -> CommunicationBus:
    """Retorna a instância global do CommunicationBus."""
    global _global_bus
    if _global_bus is None:
        _global_bus = InternalCommunicationBus()
        logger.info("communication_bus_initialized", extra={"type": "internal"})
    return _global_bus


def set_communication_bus(bus: CommunicationBus) -> None:
    """Substitui o bus global (para testes ou migração para XMPPBus)."""
    global _global_bus
    _global_bus = bus
    logger.info("communication_bus_replaced", extra={"type": type(bus).__name__})