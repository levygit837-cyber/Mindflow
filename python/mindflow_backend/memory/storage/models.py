"""Memory-specific database models."""

from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentMemoryEvent(Base):
    __tablename__ = "agent_memory_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    source_message_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentMemoryCursor(Base):
    __tablename__ = "agent_memory_cursor"
    __table_args__ = (UniqueConstraint("session_id", "agent_id", name="uq_agent_memory_cursor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    token_total: Mapped[int] = mapped_column(Integer, default=0)
    tokens_since_summary: Mapped[int] = mapped_column(Integer, default=0)
    window_index: Mapped[int] = mapped_column(Integer, default=0)
    last_summarized_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AgentMemoryWindow(Base):
    __tablename__ = "agent_memory_windows"
    __table_args__ = (UniqueConstraint("session_id", "agent_id", "window_index", name="uq_agent_memory_window"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    window_index: Mapped[int] = mapped_column(Integer)
    token_start: Mapped[int] = mapped_column(Integer)
    token_end: Mapped[int] = mapped_column(Integer)
    event_start_id: Mapped[int] = mapped_column(Integer)
    event_end_id: Mapped[int] = mapped_column(Integer)
    summary_md: Mapped[str] = mapped_column(Text)
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    coverage_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentMemoryFact(Base):
    """Legacy fact table — new facts are written to LangGraph AsyncPostgresStore.

    Kept for backwards compatibility. New code should use AgenticMemoryStore instead.
    """
    __tablename__ = "agent_memory_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    window_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_memory_windows.id", ondelete="CASCADE"))
    fact_type: Mapped[str] = mapped_column(String(32), default="insight")
    content: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentMemoryEmbedding(Base):
    __tablename__ = "agent_memory_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[int] = mapped_column(Integer)
    content_excerpt: Mapped[str] = mapped_column(Text)
    vector: Mapped[list[float]] = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SessionEmbedding(Base):
    __tablename__ = "session_embeddings"
    __table_args__ = (
        UniqueConstraint("session_id", "source_message_id", name="uq_session_embedding_message"),
        UniqueConstraint("session_id", "idempotency_key", name="uq_session_embedding_idempotency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    source_message_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    indexable: Mapped[bool] = mapped_column(default=True)
    content_kind: Mapped[str] = mapped_column(String(32), default="query")
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_status: Mapped[str] = mapped_column(String(16), default="final")
    derived_from_recall: Mapped[bool] = mapped_column(default=False)
    session_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SessionBlock(Base):
    __tablename__ = "session_blocks"
    __table_args__ = (UniqueConstraint("session_id", "sequence", name="uq_session_block"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    summary_md: Mapped[str] = mapped_column(Text)
    content_excerpt: Mapped[str] = mapped_column(Text)
    topic_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    message_start_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_messages.id"))
    message_end_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_messages.id"))
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(32), default="inferred")
    indexable: Mapped[bool] = mapped_column(default=True)
    content_kind: Mapped[str] = mapped_column(String(32), default="answer")
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_status: Mapped[str] = mapped_column(String(16), default="final")
    derived_from_recall: Mapped[bool] = mapped_column(default=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="orchestrated")
    goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pause_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_event_sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_snapshot_sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_effect_sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class AgentExecutionEvent(Base):
    __tablename__ = "agent_execution_events"
    __table_args__ = (UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_event_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_executions.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column("payload", JSON, default=dict)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    step_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentExecutionSnapshot(Base):
    __tablename__ = "agent_execution_snapshots"
    __table_args__ = (UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_snapshot_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_executions.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    snapshot_kind: Mapped[str] = mapped_column(String(32), default="checkpoint")
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    checkpoint_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    next_nodes: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_resume_point: Mapped[bool] = mapped_column(Boolean, default=False)
    state_hash: Mapped[str] = mapped_column(String(64), index=True)
    parent_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentExecutionEffect(Base):
    __tablename__ = "agent_execution_effects"
    __table_args__ = (
        UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_effect_sequence"),
        UniqueConstraint("effect_key", name="uq_agent_execution_effect_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_executions.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    effect_key: Mapped[str] = mapped_column(String(255), index=True)
    effect_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    request_json: Mapped[dict[str, Any]] = mapped_column("request", JSON, default=dict)
    response_json: Mapped[dict[str, Any]] = mapped_column("response", JSON, default=dict)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SessionRuntimeState(Base):
    __tablename__ = "session_runtime_state"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    execution_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True, index=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state_hash: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
