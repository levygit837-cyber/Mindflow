"""Message Bus - Unified communication layer for MindFlow agents.

Provides Redis pub/sub for real-time events and RabbitMQ queues for
reliable task delegation, with automatic SPADE/XMPP fallback.
"""

from .adapter import MessageBusAdapter
from .protocol import (
    AgentIdentity,
    MessageMetadata,
    MessagePriority,
    MessageTarget,
    MessageType,
    MindFlowMessage,
)
from .rabbitmq_bus import RabbitMQMessageBus
from .redis_bus import RedisMessageBus

__all__ = [
    "MessageBusAdapter",
    "MindFlowMessage",
    "MessageType",
    "MessagePriority",
    "AgentIdentity",
    "MessageTarget",
    "MessageMetadata",
    "RedisMessageBus",
    "RabbitMQMessageBus",
]