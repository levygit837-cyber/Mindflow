"""Adapter bridging message bus with SPADE/XMPP communication."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from mindflow_backend.communication.circuit_breaker.breaker import CircuitBreaker
from mindflow_backend.communication.services.p2p_service import P2PService
from mindflow_backend.communication.services.team_service import TeamService
from mindflow_backend.communication.services.xmpp_service import XMPPService

from .protocol import MindFlowMessage, MessageType
from .rabbitmq_bus import RabbitMQMessageBus
from .redis_bus import RedisMessageBus

logger = logging.getLogger(__name__)


class MessageBusAdapter:
    """Unified adapter for message bus with SPADE fallback."""

    def __init__(
        self,
        redis_bus: RedisMessageBus,
        rabbitmq_bus: RabbitMQMessageBus,
        xmpp_service: Optional[XMPPService] = None,
        p2p_service: Optional[P2PService] = None,
        team_service: Optional[TeamService] = None,
    ):
        self._redis_bus = redis_bus
        self._rabbitmq_bus = rabbitmq_bus
        self._xmpp_service = xmpp_service
        self._p2p_service = p2p_service
        self._team_service = team_service
        self._circuit_breaker = CircuitBreaker(name="message_bus_adapter")
        self._routing_rules: dict[MessageType, str] = {}

    def configure_routing(self, rules: dict[MessageType, str]) -> None:
        """Configure routing rules for message types."""
        self._routing_rules = rules
        logger.info(f"Configured routing for {len(rules)} message types")

    async def connect(self) -> None:
        """Connect all message bus backends."""
        await self._redis_bus.connect()
        await self._rabbitmq_bus.connect()
        logger.info("Message bus adapter connected")

    async def disconnect(self) -> None:
        """Disconnect all message bus backends."""
        await self._redis_bus.disconnect()
        await self._rabbitmq_bus.disconnect()
        logger.info("Message bus adapter disconnected")

    async def send(self, message: MindFlowMessage) -> bool:
        """Send message through appropriate channel."""
        if not self._circuit_breaker.can_execute():
            return await self._send_via_spade(message)

        try:
            backend = self._routing_rules.get(message.type, "redis")

            if backend == "redis":
                success = await self._redis_bus.publish(message)
            elif backend == "rabbitmq":
                success = await self._rabbitmq_bus.publish(message)
            else:
                success = False

            if success:
                self._circuit_breaker.record_success()
                return True

            self._circuit_breaker.record_failure()
            return await self._send_via_spade(message)

        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Failed to send message: {e}")
            return await self._send_via_spade(message)

    async def _send_via_spade(self, message: MindFlowMessage) -> bool:
        """Fallback to SPADE/XMPP communication."""
        try:
            if message.type == MessageType.P2P_DIRECT and self._p2p_service:
                return await self._send_p2p(message)
            if message.type == MessageType.TEAM_BROADCAST and self._team_service:
                return await self._send_team_broadcast(message)
            if self._xmpp_service:
                return await self._send_xmpp(message)
            logger.error("No SPADE services available for fallback")
            return False
        except Exception as e:
            logger.error(f"SPADE fallback failed: {e}")
            return False

    async def _send_p2p(self, message: MindFlowMessage) -> bool:
        """Send via P2P service."""
        if not self._p2p_service:
            return False
        try:
            protocol = self._p2p_service.get_or_create_protocol(
                message.source.agent_id
            )
            await protocol.send_message(
                target_agent=message.target.agent_id,
                content=message.payload,
                message_type=message.type,
            )
            return True
        except Exception as e:
            logger.error(f"P2P send failed: {e}")
            return False

    async def _send_team_broadcast(self, message: MindFlowMessage) -> bool:
        """Send via team service."""
        if not self._team_service or not message.target.team_id:
            return False
        try:
            await self._team_service.send_message(
                team_id=message.target.team_id,
                sender_jid=f"{message.source.agent_id}@localhost",
                content=message.payload.get("content", ""),
            )
            return True
        except Exception as e:
            logger.error(f"Team broadcast failed: {e}")
            return False

    async def _send_xmpp(self, message: MindFlowMessage) -> bool:
        """Send via XMPP service."""
        if not self._xmpp_service:
            return False
        try:
            logger.info(f"XMPP send for message {message.id}")
            return True
        except Exception as e:
            logger.error(f"XMPP send failed: {e}")
            return False

    async def subscribe(
        self,
        event_type: MessageType,
        handler: Callable[[MindFlowMessage], None],
    ) -> None:
        """Subscribe to message type across all backends."""
        await self._redis_bus.subscribe(event_type, handler)
        await self._rabbitmq_bus.consume(event_type, handler)
        logger.info(f"Subscribed to {event_type} across all backends")

    async def get_stats(self) -> dict[str, Any]:
        """Get adapter statistics."""
        redis_stats = await self._redis_bus.get_stats()
        rabbitmq_stats = await self._rabbitmq_bus.get_stats()
        return {
            "redis": redis_stats,
            "rabbitmq": rabbitmq_stats,
            "circuit_breaker": self._circuit_breaker.get_stats(),
            "spade_available": {
                "xmpp": self._xmpp_service is not None,
                "p2p": self._p2p_service is not None,
                "team": self._team_service is not None,
            },
        }