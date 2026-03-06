"""Base worker implementation for RabbitMQ workers."""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.credentials import PlainCredentials

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.exceptions import (
    WorkerConfigurationError,
    WorkerConnectionError,
    WorkerProcessingError,
    WorkerTimeoutError,
)
from mindflow_backend.workers.config.queues import QueueConfig
from mindflow_backend.workers.config.settings import get_worker_settings

_logger = get_logger(__name__)


class WorkerStatus(Enum):
    """Worker status states."""
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class WorkerResult:
    """Result of worker task processing."""
    
    success: bool
    message: str
    data: Dict[str, Any] | None = None
    error: Exception | None = None
    processing_time: float = 0.0
    retry_count: int = 0


class BaseWorker(ABC):
    """Abstract base class for all RabbitMQ workers."""
    
    def __init__(
        self,
        queue_config: QueueConfig,
        worker_name: str | None = None,
        settings: Any | None = None,
    ) -> None:
        """Initialize the worker.
        
        Args:
            queue_config: Configuration for the queue
            worker_name: Optional custom worker name
            settings: Optional custom settings
        """
        self.queue_config = queue_config
        self.worker_name = worker_name or f"{queue_config.worker_type}_worker"
        self.settings = settings or get_worker_settings()
        self.status = WorkerStatus.IDLE
        self._connection: Optional[AsyncioConnection] = None
        self._channel: Optional[Channel] = None
        self._retry_count = 0
        self._start_time: Optional[float] = None
        
        _logger.info(
            f"Worker {self.worker_name} initialized for queue {queue_config.get_full_queue_name()}"
        )
    
    async def start(self) -> None:
        """Start the worker and connect to RabbitMQ."""
        try:
            await self._connect()
            await self._setup_queue()
            await self._start_consuming()
            self.status = WorkerStatus.IDLE
            _logger.info(f"Worker {self.worker_name} started successfully")
        except Exception as e:
            self.status = WorkerStatus.ERROR
            raise WorkerConnectionError(
                f"Failed to start worker {self.worker_name}: {e}",
                worker_name=self.worker_name,
                service="rabbitmq",
            ) from e
    
    async def stop(self) -> None:
        """Stop the worker gracefully."""
        try:
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
            self.status = WorkerStatus.STOPPED
            _logger.info(f"Worker {self.worker_name} stopped")
        except Exception as e:
            _logger.error(f"Error stopping worker {self.worker_name}: {e}")
    
    async def _connect(self) -> None:
        """Connect to RabbitMQ."""
        credentials = PlainCredentials(
            username=self.settings.rabbitmq_username,
            password=self.settings.rabbitmq_password,
        )
        
        parameters = pika.ConnectionParameters(
            host=self.settings.rabbitmq_host,
            port=self.settings.rabbitmq_port,
            virtual_host=self.settings.rabbitmq_virtual_host,
            credentials=credentials,
            heartbeat=self.settings.heartbeat,
            connection_timeout=self.settings.connection_timeout,
        )
        
        try:
            self._connection = await pika.connect_async(parameters)
            self._channel = await self._connection.channel()
            
            # Set QoS
            await self._channel.basic_qos(
                prefetch_count=self.settings.prefetch_count
            )
            
            _logger.info(f"Worker {self.worker_name} connected to RabbitMQ")
        except Exception as e:
            raise WorkerConnectionError(
                f"Failed to connect to RabbitMQ: {e}",
                worker_name=self.worker_name,
                service="rabbitmq",
            ) from e
    
    async def _setup_queue(self) -> None:
        """Set up the queue and exchanges."""
        if not self._channel:
            raise WorkerConfigurationError(
                "No channel available for queue setup",
                worker_name=self.worker_name,
            )
        
        queue_name = self.queue_config.get_full_queue_name()
        
        # Declare queue
        await self._channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                "x-message-ttl": self.queue_config.message_ttl * 1000,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": self.queue_config.dead_letter_queue
                or f"{queue_name}.dlq",
            }
        )
        
        # Declare dead letter queue if needed
        if self.queue_config.dead_letter_queue:
            await self._channel.queue_declare(
                queue=self.queue_config.dead_letter_queue,
                durable=True,
            )
        
        _logger.info(f"Queue {queue_name} set up for worker {self.worker_name}")
    
    async def _start_consuming(self) -> None:
        """Start consuming messages from the queue."""
        if not self._channel:
            raise WorkerConfigurationError(
                "No channel available for consuming",
                worker_name=self.worker_name,
            )
        
        queue_name = self.queue_config.get_full_queue_name()
        
        await self._channel.basic_consume(
            queue=queue_name,
            on_message_callback=self._on_message,
            auto_ack=False,
        )
        
        _logger.info(f"Worker {self.worker_name} started consuming from {queue_name}")
    
    async def _on_message(
        self,
        channel: Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        """Handle incoming messages."""
        self.status = WorkerStatus.PROCESSING
        self._start_time = time.time()
        
        try:
            # Parse message
            message_data = json.loads(body.decode())
            task_id = message_data.get("task_id", "unknown")
            
            _logger.info(
                f"Worker {self.worker_name} processing task {task_id}"
            )
            
            # Process the message
            result = await self.process_message(message_data)
            
            if result.success:
                await channel.basic_ack(delivery_tag=method.delivery_tag)
                _logger.info(
                    f"Worker {self.worker_name} completed task {task_id} "
                    f"in {result.processing_time:.2f}s"
                )
            else:
                # Handle failure
                await self._handle_failure(
                    channel, method, message_data, result, task_id
                )
                
        except json.JSONDecodeError as e:
            _logger.error(
                f"Worker {self.worker_name} failed to decode message: {e}"
            )
            await channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            _logger.error(
                f"Worker {self.worker_name} unexpected error: {e}",
                exc_info=True
            )
            await channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
        finally:
            self.status = WorkerStatus.IDLE
            self._start_time = None
    
    async def _handle_failure(
        self,
        channel: Channel,
        method: pika.spec.Basic.Deliver,
        message_data: Dict[str, Any],
        result: WorkerResult,
        task_id: str,
    ) -> None:
        """Handle processing failure with retry logic."""
        self._retry_count = message_data.get("retry_count", 0) + 1
        
        if self._retry_count <= self.queue_config.max_retries:
            # Retry with delay
            await asyncio.sleep(self.queue_config.retry_delay)
            
            # Update retry count and requeue
            message_data["retry_count"] = self._retry_count
            
            await channel.basic_publish(
                exchange="",
                routing_key=self.queue_config.get_full_queue_name(),
                body=json.dumps(message_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                ),
            )
            
            await channel.basic_ack(delivery_tag=method.delivery_tag)
            
            _logger.warning(
                f"Worker {self.worker_name} retrying task {task_id} "
                f"(attempt {self._retry_count}/{self.queue_config.max_retries})"
            )
        else:
            # Max retries exceeded, send to dead letter queue
            await channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            _logger.error(
                f"Worker {self.worker_name} max retries exceeded for task {task_id}"
            )
    
    @abstractmethod
    async def process_message(self, message_data: Dict[str, Any]) -> WorkerResult:
        """Process a message. Must be implemented by subclasses.
        
        Args:
            message_data: The message data to process
            
        Returns:
            WorkerResult with processing outcome
        """
        pass
    
    def get_processing_time(self) -> float:
        """Get current task processing time."""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0
    
    def get_status(self) -> WorkerStatus:
        """Get current worker status."""
        return self.status
