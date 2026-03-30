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


class MessagePriority:
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
    ttl: Optional[int] = Field(default=30000, ge=0)
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
            metadata=MessageMetadata(correlation_id=self.id),
        )

    def create_nack(self, error: str) -> MindFlowMessage:
        """Create negative acknowledgment message."""
        return MindFlowMessage(
            type=MessageType.NACK,
            source=self.target,
            target=self.source,
            payload={"nack_for": self.id, "error": error},
            metadata=MessageMetadata(correlation_id=self.id),
        )