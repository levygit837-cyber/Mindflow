"""SPADE agent coordination schemas.

Defines the inter-agent messaging envelope and reasoning request/result
contracts as specified in agent-team-extended-contracts.md (SPADE section).

These are data contracts only — the actual SPADE/XMPP runtime is future work.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Performative(StrEnum):
    """FIPA-style message performatives."""

    REQUEST = "request"
    INFORM = "inform"
    AGREE = "agree"
    FAILURE = "failure"


class Intent(StrEnum):
    """Message intent categories."""

    DELEGATE_TASK = "delegate_task"
    REASONING_REQUEST = "reasoning_request"
    REASONING_RESULT = "reasoning_result"
    TOOL_REQUEST = "tool_request"
    TOOL_RESULT = "tool_result"
    STATUS_UPDATE = "status_update"


class ExecutionMode(StrEnum):
    """How the task should be executed."""

    SYNC = "sync"
    ASYNC = "async"
    AUTO = "auto"


class MessagePriority(StrEnum):
    """Message delivery priority."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


def _utcnow() -> datetime:
    """Return timezone-aware UTC now (avoids deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


class AgentEnvelope(BaseModel):
    """Unified SPADE message envelope for inter-agent communication."""

    schema_version: Literal["spade.v1"] = "spade.v1"
    message_id: UUID
    correlation_id: UUID
    conversation_id: str
    sender_jid: str
    recipient_jid: str | None = None
    performative: Performative
    intent: Intent
    execution_mode: ExecutionMode = ExecutionMode.AUTO
    priority: MessagePriority = MessagePriority.NORMAL
    ttl_ms: int = 60000
    created_at: datetime = Field(default_factory=_utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class ReasoningRequest(BaseModel):
    """Request to invoke the reasoning engine (LangChain/LangGraph)."""

    request_id: UUID
    task: str
    agent_type: str
    thinking_mode: str
    context: dict[str, Any] = Field(default_factory=dict)
    max_latency_ms: int = 2500
    allow_sync: bool = True


class ReasoningStatus(StrEnum):
    """Status of a reasoning result."""

    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"
    TIMEOUT = "timeout"


class ReasoningResult(BaseModel):
    """Result from a reasoning engine invocation."""

    request_id: UUID
    status: ReasoningStatus
    answer: str = ""
    thoughts: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
