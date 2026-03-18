"""Base worker implementation for RabbitMQ workers."""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

import aio_pika

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.exceptions import (
    WorkerConfigurationError,
    WorkerConnectionError,
    WorkerProcessingError,
    WorkerTimeoutError,
)
from mindflow_backend.workers.config.queues import QueueConfig
from mindflow_backend.workers.config.settings import get_worker_settings
from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope

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
        self._connection: Any | None = None
        self._channel: Any | None = None
        self._queue: Any | None = None
        self._retry_count = 0
        self._start_time: float | None = None
        self._tasks_processed = 0
        self._tasks_successful = 0
        self._tasks_failed = 0
        self._total_processing_time = 0.0
        self._last_activity: float | None = None
        self._total_retries = 0
        self._last_correlation_id: str | None = None

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
            self._channel = None
            self._queue = None
            self.status = WorkerStatus.STOPPED
            _logger.info(f"Worker {self.worker_name} stopped")
        except Exception as e:
            _logger.error(f"Error stopping worker {self.worker_name}: {e}")

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
        dead_letter_queue = self.queue_config.get_dead_letter_queue_name()

        self._queue = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-message-ttl": self.queue_config.message_ttl * 1000,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": dead_letter_queue,
            },
        )

        await self._channel.declare_queue(
            dead_letter_queue,
            durable=True,
        )

        _logger.info(f"Queue {queue_name} set up for worker {self.worker_name}")

    async def _start_consuming(self) -> None:
        """Start consuming messages from the queue."""
        if not self._queue:
            raise WorkerConfigurationError(
                "No queue available for consuming",
                worker_name=self.worker_name,
            )

        await self._queue.consume(self._on_message, no_ack=False)

        _logger.info(
            f"Worker {self.worker_name} started consuming from {self.queue_config.get_full_queue_name()}"
        )

    async def _on_message(self, message: Any) -> None:
        """Handle incoming messages."""
        self.status = WorkerStatus.PROCESSING
        self._start_time = time.time()

        try:
            # Parse message
            message_data = self._normalize_message_data(json.loads(message.body.decode()))
            task_id = message_data.get("task_id", "unknown")
            self._last_correlation_id = message_data.get("correlation_id")

            _logger.info(f"Worker {self.worker_name} processing task {task_id}")

            # Process the message
            result = await self.process_message(message_data)
            processing_time = result.processing_time or self.get_processing_time()
            result.processing_time = processing_time
            self._record_processing_outcome(
                success=result.success,
                processing_time=processing_time,
            )

            if result.success:
                await message.ack()
                _logger.info(
                    f"Worker {self.worker_name} completed task {task_id} "
                    f"in {result.processing_time:.2f}s"
                )
            else:
                # Handle failure
                await self._handle_failure(message, message_data, result, task_id)

        except json.JSONDecodeError as e:
            self._record_processing_outcome(
                success=False,
                processing_time=self.get_processing_time(),
            )
            _logger.error(f"Worker {self.worker_name} failed to decode message: {e}")
            await message.reject(requeue=False)

        except Exception as e:
            self._record_processing_outcome(
                success=False,
                processing_time=self.get_processing_time(),
            )
            _logger.error(
                f"Worker {self.worker_name} unexpected error: {e}",
                exc_info=True
            )
            await message.reject(requeue=True)

        finally:
            self.status = WorkerStatus.IDLE
            self._start_time = None

    async def _handle_failure(
        self,
        message: Any,
        message_data: Dict[str, Any],
        result: WorkerResult,
        task_id: str,
    ) -> None:
        """Handle processing failure with retry logic."""
        retry_policy = self.queue_config.get_retry_policy()
        self._retry_count = message_data.get("retry_count", 0) + 1
        self._total_retries += 1

        if self._retry_count <= retry_policy.max_retries:
            if not self._channel:
                raise WorkerConfigurationError(
                    "No channel available for retry publish",
                    worker_name=self.worker_name,
                )

            # Retry with delay
            await asyncio.sleep(retry_policy.get_delay_for_attempt(self._retry_count))

            # Update retry count and requeue
            message_data["retry_count"] = self._retry_count

            retry_message = aio_pika.Message(
                body=json.dumps(message_data, default=str).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )

            await self._channel.default_exchange.publish(
                retry_message,
                routing_key=self.queue_config.get_full_queue_name(),
            )

            await message.ack()

            _logger.warning(
                f"Worker {self.worker_name} retrying task {task_id} "
                f"(attempt {self._retry_count}/{retry_policy.max_retries})"
            )
        else:
            # Max retries exceeded, send to dead letter queue
            await message.reject(requeue=False)

            _logger.error(
                f"Worker {self.worker_name} max retries exceeded for task {task_id}"
            )

    def _normalize_message_data(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize envelope and legacy payload formats for consumers."""
        if "schema_version" in message_data and "payload" in message_data:
            retry_count = message_data.get("retry_count")
            envelope_data = {k: v for k, v in message_data.items() if k != "retry_count"}
            envelope = QueueMessageEnvelope.model_validate(envelope_data)
            normalized = {
                **envelope.payload,
                "schema_version": envelope.schema_version,
                "task_type": envelope.task_type,
                "task_id": envelope.task_id,
                "session_id": envelope.session_id,
                "run_id": envelope.run_id,
                "correlation_id": envelope.correlation_id,
                "idempotency_key": envelope.idempotency_key,
                "created_at": envelope.created_at,
                "metadata": envelope.metadata,
            }
            if retry_count is not None:
                normalized["retry_count"] = retry_count
            return normalized

        task_data = message_data.get("task_data")
        if isinstance(task_data, dict):
            normalized = {**task_data}
            for key in (
                "task_type",
                "task_id",
                "session_id",
                "priority",
                "agent_type",
                "system_component",
                "research_domain",
                "metadata",
            ):
                if key in message_data:
                    normalized[key] = message_data[key]
            return normalized

        payload = message_data.get("payload")
        if isinstance(payload, dict):
            normalized = {**payload}
            for key in ("task_type", "task_id", "session_id", "metadata"):
                if key in message_data:
                    normalized[key] = message_data[key]
            return normalized

        return message_data

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

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get current runtime metrics for monitoring and health reports."""
        average_processing_time = (
            self._total_processing_time / self._tasks_processed
            if self._tasks_processed
            else 0.0
        )
        return {
            "tasks_processed": self._tasks_processed,
            "tasks_successful": self._tasks_successful,
            "tasks_failed": self._tasks_failed,
            "average_processing_time": average_processing_time,
            "last_activity": self._last_activity,
            "retry_count": self._total_retries,
            "last_correlation_id": self._last_correlation_id,
        }

    def get_status(self) -> WorkerStatus:
        """Get current worker status."""
        return self.status

    def _record_processing_outcome(self, *, success: bool, processing_time: float) -> None:
        """Update worker runtime counters after a processing attempt."""
        self._tasks_processed += 1
        self._last_activity = time.time()
        self._total_processing_time += max(processing_time, 0.0)
        if success:
            self._tasks_successful += 1
        else:
            self._tasks_failed += 1
