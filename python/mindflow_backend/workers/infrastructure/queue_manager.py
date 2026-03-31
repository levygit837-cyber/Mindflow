"""Queue manager for RabbitMQ operations."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aio_pika

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.config.queues import QueueConfig, get_all_queue_configs
from mindflow_backend.workers.config.settings import get_worker_settings
from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope

_logger = get_logger(__name__)


class QueueManager:
    """Manages RabbitMQ queues and message publishing."""
    
    def __init__(self) -> None:
        """Initialize the queue manager."""
        self.settings = get_worker_settings()
        self._connection: Any | None = None
        self._channel: Any | None = None
        self._queue_configs: dict[str, QueueConfig] = {}
        self._initialized = False
        self._published_idempotency_keys: set[str] = set()

        # Load all queue configurations
        for config in get_all_queue_configs():
            self._queue_configs[config.name] = config

    async def initialize(self) -> None:
        """Initialize connection to RabbitMQ and set up queues."""
        if self._initialized:
            return

        try:
            await self._connect()
            await self._setup_all_queues()
            self._initialized = True
            _logger.info("QueueManager initialized successfully")
        except Exception as e:
            _logger.error(f"Failed to initialize QueueManager: {e}")
            raise
    
    async def close(self) -> None:
        """Close connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._channel = None
        self._initialized = False
        _logger.info("QueueManager connection closed")

    async def _connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            self._connection = await aio_pika.connect_robust(
                host=self.settings.rabbitmq_host,
                port=self.settings.rabbitmq_port,
                login=self.settings.rabbitmq_username,
                password=self.settings.rabbitmq_password,
                virtualhost=self.settings.rabbitmq_virtual_host,
                timeout=self.settings.connection_timeout,
                heartbeat=self.settings.heartbeat,
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self.settings.prefetch_count)

            _logger.info("QueueManager connected to RabbitMQ")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to RabbitMQ: {e}") from e

    async def _setup_all_queues(self) -> None:
        """Set up all configured queues."""
        if not self._channel:
            raise RuntimeError("No channel available for queue setup")

        for queue_config in self._queue_configs.values():
            await self._setup_queue(queue_config)

        _logger.info(f"Set up {len(self._queue_configs)} queues")

    async def _setup_queue(self, queue_config: QueueConfig) -> None:
        """Set up a single queue."""
        if not self._channel:
            raise RuntimeError("No channel available for queue setup")

        queue_name = queue_config.get_full_queue_name()
        dead_letter_queue = queue_config.get_dead_letter_queue_name()

        # Declare main queue
        await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-message-ttl": queue_config.message_ttl * 1000,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": dead_letter_queue,
            },
        )

        # Declare dead letter queue
        await self._channel.declare_queue(
            dead_letter_queue,
            durable=True,
        )

        _logger.debug(f"Queue {queue_name} set up")

    async def publish_message(
        self,
        queue_name: str,
        message_data: dict[str, Any],
        priority: int | None = None,
        delay: int | None = None,
    ) -> bool:
        """Publish a message to a queue.

        Args:
            queue_name: Name of the target queue
            message_data: Message data to publish
            priority: Optional message priority (0-9)
            delay: Optional delay in seconds before message becomes available

        Returns:
            True if message was published successfully
        """
        if not self._initialized:
            await self.initialize()

        if queue_name not in self._queue_configs:
            _logger.error(f"Unknown queue: {queue_name}")
            return False

        if not self._channel:
            raise RuntimeError("No channel available for publish")

        queue_config = self._queue_configs[queue_name]
        queue_full_name = queue_config.get_full_queue_name()

        idempotency_key: str | None = None

        if "schema_version" in message_data and "payload" in message_data:
            envelope = QueueMessageEnvelope.model_validate(message_data)
            if envelope.idempotency_key in self._published_idempotency_keys:
                _logger.debug(
                    "Skipping duplicate publish for idempotency key %s",
                    envelope.idempotency_key,
                )
                return True
            enhanced_message = envelope.model_dump(mode="json")
            idempotency_key = envelope.idempotency_key
        else:
            enhanced_message = {
                **message_data,
                "metadata": {
                    "queue_name": queue_name,
                    "published_at": asyncio.get_event_loop().time(),
                    "priority": priority,
                    "delay": delay,
                },
            }

        message = aio_pika.Message(
            body=json.dumps(enhanced_message).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            priority=priority,
            content_type="application/json",
            headers={"x-delay": delay * 1000} if delay else None,
        )

        try:
            await self._channel.default_exchange.publish(
                message,
                routing_key=queue_full_name,
            )
            if idempotency_key is not None:
                self._published_idempotency_keys.add(idempotency_key)

            _logger.debug(f"Message published to {queue_full_name}")
            return True

        except Exception as e:
            _logger.error(f"Failed to publish message to {queue_full_name}: {e}")
            return False

    async def get_queue_info(self, queue_name: str) -> dict[str, Any] | None:
        """Get information about a queue."""
        if not self._initialized:
            await self.initialize()

        if queue_name not in self._queue_configs:
            return None

        if not self._channel:
            raise RuntimeError("No channel available for queue inspection")

        queue_config = self._queue_configs[queue_name]
        queue_full_name = queue_config.get_full_queue_name()

        try:
            queue = await self._channel.declare_queue(
                queue_full_name,
                passive=True,
            )
            declaration = getattr(queue, "declaration_result", None)

            return {
                "queue_name": queue_full_name,
                "message_count": getattr(declaration, "message_count", None),
                "consumer_count": getattr(declaration, "consumer_count", None),
                "config": {
                    "durable": True,
                    "message_ttl": queue_config.message_ttl,
                    "max_retries": queue_config.max_retries,
                    "concurrency": queue_config.concurrency,
                },
            }

        except Exception as e:
            _logger.error(f"Failed to get queue info for {queue_full_name}: {e}")
            return None

    async def purge_queue(self, queue_name: str) -> bool:
        """Purge all messages from a queue."""
        if not self._initialized:
            await self.initialize()

        if queue_name not in self._queue_configs:
            return False

        if not self._channel:
            raise RuntimeError("No channel available for queue purge")

        queue_full_name = self._queue_configs[queue_name].get_full_queue_name()

        try:
            queue = await self._channel.declare_queue(queue_full_name, passive=True)
            await queue.purge()
            _logger.info(f"Purged queue {queue_full_name}")
            return True

        except Exception as e:
            _logger.error(f"Failed to purge queue {queue_full_name}: {e}")
            return False

    async def delete_queue(self, queue_name: str, if_unused: bool = False) -> bool:
        """Delete a queue."""
        if not self._initialized:
            await self.initialize()

        if queue_name not in self._queue_configs:
            return False

        if not self._channel:
            raise RuntimeError("No channel available for queue delete")

        queue_full_name = self._queue_configs[queue_name].get_full_queue_name()

        try:
            queue = await self._channel.declare_queue(queue_full_name)
            await queue.delete(if_unused=if_unused)
            _logger.info(f"Deleted queue {queue_full_name}")
            return True

        except Exception as e:
            _logger.error(f"Failed to delete queue {queue_full_name}: {e}")
            return False
    
    def get_all_queue_configs(self) -> dict[str, QueueConfig]:
        """Get all queue configurations."""
        return self._queue_configs.copy()
    
    def get_queue_config(self, queue_name: str) -> Optional[QueueConfig]:
        """Get configuration for a specific queue."""
        return self._queue_configs.get(queue_name)
    
    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the queue system."""
        if not self._initialized:
            await self.initialize()
        
        health_status = {
            "connection_status": "connected" if self._connection and not self._connection.is_closed else "disconnected",
            "channel_status": "open" if self._channel and not self._channel.is_closed else "closed",
            "total_queues": len(self._queue_configs),
            "queue_details": {},
        }
        
        # Get info for each queue
        for queue_name in self._queue_configs:
            queue_info = await self.get_queue_info(queue_name)
            if queue_info:
                health_status["queue_details"][queue_name] = {
                    "message_count": queue_info["message_count"],
                    "consumer_count": queue_info["consumer_count"],
                }
        
        return health_status


# Global queue manager instance
_queue_manager: Optional[QueueManager] = None


def get_queue_manager() -> QueueManager:
    """Get the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager
