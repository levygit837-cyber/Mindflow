"""Redis pub/sub implementation for real-time agent communication."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from mindflow_backend.communication.circuit_breaker.breaker import CircuitBreaker
from mindflow_backend.infra.redis import get_async_redis

from .protocol import MindFlowMessage, MessageType

logger = logging.getLogger(__name__)


class RedisMessageBus:
    """Redis-based message bus for real-time pub/sub communication."""

    def __init__(
        self,
        redis: Optional[Redis] = None,
        channel_prefix: str = "mindflow:bus:",
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self._redis = redis
        self._channel_prefix = channel_prefix
        self._pubsub: Optional[PubSub] = None
        self._subscribers: dict[str, list[Callable]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            name="redis_message_bus"
        )

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._redis is None:
            self._redis = await get_async_redis()
        self._pubsub = self._redis.pubsub()
        logger.info("Redis message bus connected")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.close()
        logger.info("Redis message bus disconnected")

    def _channel_name(self, event_type: str) -> str:
        """Generate channel name for event type."""
        return f"{self._channel_prefix}{event_type}"

    async def publish(self, message: MindFlowMessage) -> bool:
        """Publish message to appropriate channel."""
        if not self._circuit_breaker.can_execute():
            logger.warning("Circuit breaker open, message not published")
            return False

        try:
            channel = self._channel_name(message.type)
            data = message.to_json()
            await self._redis.publish(channel, data)
            self._circuit_breaker.record_success()
            logger.debug(f"Published message {message.id} to {channel}")
            return True
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Failed to publish message: {e}")
            return False

    async def subscribe(
        self,
        event_type: MessageType,
        handler: Callable[[MindFlowMessage], None],
    ) -> None:
        """Subscribe to messages of specific type."""
        channel = self._channel_name(event_type)
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(handler)

        if self._pubsub:
            await self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to {channel}")

    async def unsubscribe(
        self,
        event_type: MessageType,
        handler: Callable[[MindFlowMessage], None],
    ) -> None:
        """Unsubscribe from message type."""
        channel = self._channel_name(event_type)
        if channel in self._subscribers:
            self._subscribers[channel].remove(handler)
            if not self._subscribers[channel]:
                del self._subscribers[channel]
                if self._pubsub:
                    await self._pubsub.unsubscribe(channel)

    async def start_listener(self) -> None:
        """Start message listener loop."""
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("Redis message listener started")

    async def _listen_loop(self) -> None:
        """Main message processing loop."""
        while self._running and self._pubsub:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message and message["type"] == "message":
                    await self._handle_message(
                        message["channel"].decode(),
                        message["data"].decode(),
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in listener loop: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, channel: str, data: str) -> None:
        """Process incoming message."""
        try:
            message = MindFlowMessage.from_json(data)
            if message.is_expired():
                logger.debug(f"Message {message.id} expired, skipping")
                return

            handlers = self._subscribers.get(channel, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Handler error for {channel}: {e}")
        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """Get bus statistics."""
        return {
            "connected": self._redis is not None,
            "running": self._running,
            "subscribers": len(self._subscribers),
            "circuit_breaker": self._circuit_breaker.get_stats(),
        }