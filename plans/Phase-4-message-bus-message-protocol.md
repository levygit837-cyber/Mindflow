# Plano de Implementação da Fase 4: Message Bus (Redis + RabbitMQ)

## 📋 Sumário Executivo

Com base na análise completa do codebase, proponho uma arquitetura de **Message Bus Dual-Layer** que combina Redis (pub/sub para eventos em tempo real) e RabbitMQ (filas para tarefas assíncronas) com um protocolo de mensagens unificado.

## 🏗️ Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────┐
│                    MESSAGE BUS ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Redis      │  │  RabbitMQ   │  │   SPADE     │         │
│  │   (Pub/Sub)  │  │  (Queues)   │  │  (Fallback) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────┴────────────────┴────────────────┴──────┐         │
│  │           MessageBusAdapter (Unified)          │         │
│  └──────┬────────────────┬────────────────┬──────┘         │
│         │                │                │                 │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐         │
│  │   Protocol   │  │  Circuit    │  │   Router    │         │
│  │   Handler    │  │  Breaker    │  │   Layer     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Protocolo de Mensagens Unificado

### Estrutura Base (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MindFlowMessage",
  "type": "object",
  "required": ["id", "type", "source", "target", "timestamp", "version"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Identificador único da mensagem"
    },
    "type": {
      "type": "string",
      "enum": [
        "task_delegation",
        "task_result", 
        "memory_sync",
        "team_broadcast",
        "p2p_direct",
        "heartbeat",
        "ack",
        "nack"
      ],
      "description": "Tipo do evento/mensagem"
    },
    "source": {
      "type": "object",
      "properties": {
        "agent_id": {"type": "string"},
        "container_id": {"type": "string"},
        "service": {"type": "string"}
      },
      "required": ["agent_id"]
    },
    "target": {
      "type": "object",
      "properties": {
        "agent_id": {"type": "string"},
        "team_id": {"type": "string"},
        "broadcast": {"type": "boolean"}
      }
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "version": {
      "type": "string",
      "const": "1.0"
    },
    "payload": {
      "type": "object",
      "description": "Dados específicos do tipo de mensagem"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "correlation_id": {"type": "string"},
        "reply_to": {"type": "string"},
        "ttl": {"type": "integer"},
        "priority": {"type": "integer", "minimum": 0, "maximum": 10}
      }
    }
  }
}
```

### Tipos de Mensagem Específicos

#### 1. `task_delegation`

```json
{
  "type": "task_delegation",
  "payload": {
    "task_id": "uuid",
    "task_type": "analysis|generation|execution",
    "description": "string",
    "context": {
      "session_id": "string",
      "conversation_history": [],
      "tools_available": []
    },
    "requirements": {
      "capabilities": [],
      "timeout_ms": 30000,
      "priority": 5
    }
  }
}
```

#### 2. `task_result`

```json
{
  "type": "task_result",
  "payload": {
    "task_id": "uuid",
    "status": "success|failure|partial",
    "result": {
      "data": {},
      "artifacts": [],
      "metrics": {
        "execution_time_ms": 1500,
        "tokens_used": 500
      }
    },
    "error": {
      "code": "string",
      "message": "string",
      "stack_trace": "string"
    }
  }
}
```

#### 3. `memory_sync`

```json
{
  "type": "memory_sync",
  "payload": {
    "sync_type": "full|incremental|delta",
    "memory_scope": "session|task|global",
    "data": {
      "key": "string",
      "value": {},
      "version": 1,
      "checksum": "sha256"
    }
  }
}
```

#### 4. `team_broadcast`

```json
{
  "type": "team_broadcast",
  "payload": {
    "team_id": "string",
    "message_type": "announcement|request|update",
    "content": "string",
    "attachments": []
  }
}
```

#### 5. `p2p_direct`

```json
{
  "type": "p2p_direct",
  "payload": {
    "conversation_id": "string",
    "message_type": "request|response|notification",
    "content": {},
    "requires_ack": true
  }
}
```

## 🔧 Implementação dos Módulos

### 1. `protocol.py` - Definição do Protocolo

```python
"""Message protocol definitions for MindFlow agent communication."""

from __future__ import annotations
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(StrEnum):
    """Supported message types in the MindFlow message bus."""
    TASK_DELEGATION = "task_delegation"
    TASK_RESULT = "task_result"
    MEMORY_SYNC = "memory_sync"
    TEAM_BROADCAST = "team_broadcast"
    P2P_DIRECT = "p2p_direct"
    HEARTBEAT = "heartbeat"
    ACK = "ack"
    NACK = "nack"


class MessagePriority(int):
    """Message priority levels (0=lowest, 10=highest)."""
    LOW = 0
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class AgentIdentity(BaseModel):
    """Agent identification in message protocol."""
    agent_id: str
    container_id: Optional[str] = None
    service: Optional[str] = None


class MessageTarget(BaseModel):
    """Message destination specification."""
    agent_id: Optional[str] = None
    team_id: Optional[str] = None
    broadcast: bool = False


class MessageMetadata(BaseModel):
    """Message metadata for routing and tracking."""
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[int] = Field(default=30000, ge=0)  # milliseconds
    priority: int = Field(default=MessagePriority.NORMAL, ge=0, le=10)


class MindFlowMessage(BaseModel):
    """Unified message format for all agent communication."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: MessageType
    source: AgentIdentity
    target: MessageTarget
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    version: str = "1.0"
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> MindFlowMessage:
        """Deserialize message from JSON string."""
        return cls.model_validate_json(data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for transport."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MindFlowMessage:
        """Create from dictionary."""
        return cls.model_validate(data)

    def is_expired(self) -> bool:
        """Check if message has exceeded TTL."""
        if not self.metadata.ttl:
            return False
        msg_time = datetime.fromisoformat(self.timestamp)
        elapsed = (datetime.now(UTC) - msg_time).total_seconds() * 1000
        return elapsed > self.metadata.ttl

    def create_ack(self) -> MindFlowMessage:
        """Create acknowledgment message."""
        return MindFlowMessage(
            type=MessageType.ACK,
            source=self.target,
            target=self.source,
            payload={"ack_for": self.id},
            metadata=MessageMetadata(correlation_id=self.id)
        )

    def create_nack(self, error: str) -> MindFlowMessage:
        """Create negative acknowledgment message."""
        return MindFlowMessage(
            type=MessageType.NACK,
            source=self.target,
            target=self.source,
            payload={"nack_for": self.id, "error": error},
            metadata=MessageMetadata(correlation_id=self.id)
        )
```

### 2. `redis_bus.py` - Redis Pub/Sub

```python
"""Redis pub/sub implementation for real-time agent communication."""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Callable, Optional

from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from mindflow_backend.infra.redis import get_async_redis
from mindflow_backend.communication.circuit_breaker import CircuitBreaker
from .protocol import MindFlowMessage, MessageType

logger = logging.getLogger(__name__)


class RedisMessageBus:
    """Redis-based message bus for real-time pub/sub communication."""

    def __init__(
        self,
        redis: Optional[Redis] = None,
        channel_prefix: str = "mindflow:bus:",
        circuit_breaker: Optional[CircuitBreaker] = None
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
        handler: Callable[[MindFlowMessage], None]
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
        handler: Callable[[MindFlowMessage], None]
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
                    timeout=1.0
                )
                if message and message["type"] == "message":
                    await self._handle_message(
                        message["channel"].decode(),
                        message["data"].decode()
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
            "circuit_breaker": self._circuit_breaker.get_stats()
        }
```

### 3. `rabbitmq_bus.py` - RabbitMQ Queues

```python
"""RabbitMQ implementation for reliable task queue communication."""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Callable, Optional

import aio_pika
from aio_pika import Message as AioPikaMessage, DeliveryMode, ExchangeType

from mindflow_backend.communication.circuit_breaker import CircuitBreaker
from .protocol import MindFlowMessage, MessageType

logger = logging.getLogger(__name__)


class RabbitMQMessageBus:
    """RabbitMQ-based message bus for reliable task queuing."""

    def __init__(
        self,
        connection_url: str = "amqp://guest:guest@localhost:5672/",
        exchange_name: str = "mindflow.tasks",
        queue_prefix: str = "mindflow.queue.",
        circuit_breaker: Optional[CircuitBreaker] = None
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
            self._connection = await aio_pika.connect_robust(
                self._connection_url
            )
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                ExchangeType.TOPIC,
                durable=True
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
            aio_message = AioPikaMessage(
                body=message.to_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                expiration=message.metadata.ttl / 1000 if message.metadata.ttl else None,
                priority=message.metadata.priority,
                correlation_id=message.metadata.correlation_id,
                reply_to=message.metadata.reply_to
            )

            await self._exchange.publish(aio_message, routing_key=routing_key)
            self._circuit_breaker.record_success()
            logger.debug(f"Published message {message.id} with key {routing_key}")
            return True
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Failed to publish message: {e}")
            return False

    async def declare_queue(
        self,
        event_type: MessageType,
        durable: bool = True
    ) -> aio_pika.Queue:
        """Declare queue for event type."""
        queue_name = self._queue_name(event_type)
        if queue_name not in self._queues:
            queue = await self._channel.declare_queue(
                queue_name,
                durable=durable,
                arguments={
                    "x-message-ttl": 86400000,  # 24 hours
                    "x-max-length": 10000
                }
            )
            # Bind queue to exchange with routing pattern
            await queue.bind(
                self._exchange,
                routing_key=f"{event_type}.*"
            )
            self._queues[queue_name] = queue
            logger.info(f"Declared queue {queue_name}")
        return self._queues[queue_name]

    async def consume(
        self,
        event_type: MessageType,
        handler: Callable[[MindFlowMessage], None]
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
                    # Message will be requeued due to exception

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
                "consumers": declaration_result.consumer_count
            }
        return {"name": queue_name, "messages": 0, "consumers": 0}

    async def get_stats(self) -> dict[str, Any]:
        """Get bus statistics."""
        stats = {
            "connected": self._connection is not None and not self._connection.is_closed,
            "running": self._running,
            "queues": {},
            "circuit_breaker": self._circuit_breaker.get_stats()
        }
        for event_type in self._consumers:
            stats["queues"][event_type] = await self.get_queue_stats(event_type)
        return stats
```

### 4. `adapter.py` - Bridge com SPADE

```python
"""Adapter bridging message bus with SPADE/XMPP communication."""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Optional

from mindflow_backend.communication.services import XMPPService, P2PService, TeamService
from mindflow_backend.communication.circuit_breaker import CircuitBreaker
from .protocol import MindFlowMessage, MessageType
from .redis_bus import RedisMessageBus
from .rabbitmq_bus import RabbitMQMessageBus

logger = logging.getLogger(__name__)


class MessageBusAdapter:
    """Unified adapter for message bus with SPADE fallback."""

    def __init__(
        self,
        redis_bus: RedisMessageBus,
        rabbitmq_bus: RabbitMQMessageBus,
        xmpp_service: Optional[XMPPService] = None,
        p2p_service: Optional[P2PService] = None,
        team_service: Optional[TeamService] = None
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
            # Determine routing based on message type
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
            else:
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
            elif message.type == MessageType.TEAM_BROADCAST and self._team_service:
                return await self._send_team_broadcast(message)
            elif self._xmpp_service:
                return await self._send_xmpp(message)
            else:
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
                message_type=message.type
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
                content=message.payload.get("content", "")
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
            # Implement XMPP send logic
            logger.info(f"XMPP send for message {message.id}")
            return True
        except Exception as e:
            logger.error(f"XMPP send failed: {e}")
            return False

    async def subscribe(
        self,
        event_type: MessageType,
        handler: callable
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
                "team": self._team_service is not None
            }
        }
```

## 📁 Estrutura de Arquivos

```
python/mindflow_backend/runtime/message_bus/
├── __init__.py          # Exports principais
├── protocol.py          # Definição do protocolo de mensagens
├── redis_bus.py         # Implementação Redis pub/sub
├── rabbitmq_bus.py      # Implementação RabbitMQ queues
└── adapter.py           # Bridge com SPADE/XMPP
```

## 🔌 Integração com Código Existente

### 1. Circuit Breaker

- Reutilizar `communication/circuit_breaker/breaker.py`
- Configurar thresholds: 5 falhas, 30s recovery, 3 half-open calls

### 2. Redis Infrastructure

- Reutilizar `infra/redis.py` (`get_async_redis()`)
- Adicionar `aio-pika` para RabbitMQ

### 3. SPADE Services

- Bridge com `XMPPService`, `P2PService`, `TeamService`
- Fallback automático quando circuit breaker abre

### 4. Runtime Integration

- Integrar com `RuntimeExecutor` para task delegation
- Conectar com `MemoryIntegration` para memory sync

## 🧪 Plano de Testes

1. **Unit Tests**: Cada módulo com mocks
2. **Integration Tests**: Redis/RabbitMQ containers
3. **End-to-End Tests**: Fluxo completo de delegação
4. **Fallback Tests**: Simular falhas de backend

## 📊 Métricas e Monitoramento

- Mensagens publicadas/processadas por tipo
- Latência de entrega
- Taxa de sucesso/falha
- Circuit breaker state
- Queue depths (RabbitMQ)

## 🚀 Próximos Passos

1. Implementar `protocol.py` com validação Pydantic
2. Criar `redis_bus.py` com pub/sub básico
3. Criar `rabbitmq_bus.py` com filas persistentes
4. Implementar `adapter.py` com fallback SPADE
5. Integrar com `RuntimeExecutor` e `MemoryIntegration`
6. Adicionar testes unitários e de integração
7. Configurar métricas e monitoramento

---

**Deseja que eu implemente este plano em modo ACT? Posso começar pelo `protocol.py` e depois seguir com os demais módulos.**
