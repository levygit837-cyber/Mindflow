"""Shared contracts for the RabbitMQ worker subsystem."""

from .interfaces.consumer import MessageConsumer
from .interfaces.message_bus import MessageBus
from .interfaces.publisher import MessagePublisher
from .interfaces.serializer import JsonMessageSerializer, MessageSerializer
from .schemas.envelope import QueueMessageEnvelope
from .schemas.health import WorkerHealthSnapshot
from .schemas.result import MessageProcessingResult
from .schemas.retry_policy import RetryPolicy

__all__ = [
    "JsonMessageSerializer",
    "MessageBus",
    "MessageConsumer",
    "MessageProcessingResult",
    "MessagePublisher",
    "MessageSerializer",
    "QueueMessageEnvelope",
    "RetryPolicy",
    "WorkerHealthSnapshot",
]
