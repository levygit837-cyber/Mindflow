"""RabbitMQ implementation for reliable task queue communication."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message as AioPikaMessage

from mindflow_backend.communication.circuit_breaker.breaker import CircuitBreaker

from .protocol import MindFlowMessage, MessageType

logger = logging.getLogger(__name__)


class RabbitMQMessageBus:
    """RabbitMQ-based message bus for reliable task queuing."""

    def __init__(
        self,
        connection_url: str = "amqp://guest:guest@localhost:5672/",
        exchange_name: str = "mindflow.tasks",
        queue_prefix: str = "mindflow.queue.",
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self._connection_url = connection_url
        self._exchange_name = exchange_name
        self._queue_prefix = queue_prefix
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._exchange: Optional[aio_pika.Exchange] = None
        self._queues: dict[str, aio_pika.Queue] = {}
        self._consumers: dict[str, Callable] = {}
        self._running = False
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            name="rabbitmq_message_bus"
        )

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self._connection = await aio_pika.connect_robust(self._connection_url)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )
            logger.info("RabbitMQ message bus connected")
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        self._running = False
        if self._connection:
            await self._connection.close()
        logger.info("RabbitMQ message bus disconnected")

    def _queue_name(self, event_type: str) -> str:
        """Generate queue name for event type."""
        return f"{self._queue_prefix}{event_type}"

    def _routing_key(self, message: MindFlowMessage) -> str:
        """Generate routing key for message."""
        parts = [message.type]
        if message.target.agent_id:
            parts.append(f"agent.{message.target.agent_id}")
        if message.target.team_id:
            parts.append(f"team.{message.target.team_id}")
        return ".".join(parts)

    async def publish(self, message: MindFlowMessage) -> bool:
        """Publish message to task queue."""
        if not self._circuit_breaker.can_execute():
            logger.warning("Circuit breaker open, message not published")
            return False

        try:
            if not self._exchange:
                await self.connect()

            routing_key = self._routing_key(message)
            expiration = (
                message.metadata.ttl / 1000 if message.metadata.ttl else None
            )
            aio_message = AioPikaMessage(
                body=message.to_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                expiration=expiration,
                priority=message.metadata.priority,
                correlation_id=message.metadata.correlation_id,
                reply_to=message.metadata.reply_to,
            )

            await self._exchange.publish(aio_message, routing_key=routing_key)
            self._circuit_breaker.record_success()
            logger.debug(
                f"Published message {message.id} with key {routing_key}"
            )
            return True
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Failed to publish message: {e}")
            return False

    async def declare_queue(
        self,
        event_type: MessageType,
        durable: bool = True,
    ) -> aio_pika.Queue:
        """Declare queue for event type."""
        queue_name = self._queue_name(event_type)
        if queue_name not in self._queues:
            queue = await self._channel.declare_queue(
                queue_name,
                durable=durable,
                arguments={
                    "x-message-ttl": 86400000,
                    "x-max-length": 10000,
                },
            )
            await queue.bind(
                self._exchange,
                routing_key=f"{event_type}.*",
            )
            self._queues[queue_name] = queue
            logger.info(f"Declared queue {queue_name}")
        return self._queues[queue_name]

    async def consume(
        self,
        event_type: MessageType,
        handler: Callable[[MindFlowMessage], None],
    ) -> None:
        """Start consuming messages from queue."""
        queue = await self.declare_queue(event_type)
        self._consumers[event_type] = handler

        async def process_message(message: aio_pika.IncomingMessage) -> None:
            async with message.process():
                try:
                    mf_message = MindFlowMessage.from_json(
                        message.body.decode()
                    )
                    if mf_message.is_expired():
                        logger.debug(f"Message {mf_message.id} expired")
                        return

                    if asyncio.iscoroutinefunction(handler):
                        await handler(mf_message)
                    else:
                        handler(mf_message)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        await queue.consume(process_message)
        logger.info(f"Started consuming from {queue.name}")

    async def start_consumer(self) -> None:
        """Start all registered consumers."""
        self._running = True
        for event_type, handler in self._consumers.items():
            await self.consume(event_type, handler)
        logger.info("RabbitMQ consumers started")

    async def get_queue_stats(self, event_type: MessageType) -> dict[str, Any]:
        """Get queue statistics."""
        queue_name = self._queue_name(event_type)
        if queue_name in self._queues:
            queue = self._queues[queue_name]
            declaration_result = await queue.declare()
            return {
                "name": queue_name,
                "messages": declaration_result.message_count,
                "consumers": declaration_result.consumer_count,
            }
        return {"name": queue_name, "messages": 0, "consumers": 0}

    async def get_stats(self) -> dict[str, Any]:
        """Get bus statistics."""
        is_connected = (
            self._connection is not None and not self._connection.is_closed
        )
        stats: dict[str, Any] = {
            "connected": is_connected,
            "running": self._running,
            "queues": {},
            "circuit_breaker": self._circuit_breaker.get_stats(),
        }
        for event_type in self._consumers:
            stats["queues"][event_type] = await self.get_queue_stats(event_type)
        return stats