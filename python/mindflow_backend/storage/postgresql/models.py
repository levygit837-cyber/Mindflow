from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    # owner_id: identifies the API key / user that created this session.
    # NULL means legacy record created before ownership was enforced.
    owner_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(50))  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


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


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class NeuralDocument(Base):
    __tablename__ = "neural_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    folder_path: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)




class SessionRetriever(Base):
    __tablename__ = "session_retrievers"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    context_window_start: Mapped[int] = mapped_column(Integer, nullable=False)
    context_window_end: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieval_query: Mapped[str] = mapped_column(Text, default="")
    retrieval_mode: Mapped[str] = mapped_column(String(10), default="range")
    included_sessions: Mapped[list[UUID]] = mapped_column(JSON, default=list)
    excluded_sessions: Mapped[list[UUID]] = mapped_column(JSON, default=list)
    max_results: Mapped[int] = mapped_column(Integer, default=10)
    min_relevance_score: Mapped[float] = mapped_column(Float, default=0.3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    summarization_reviews: Mapped[list["SummarizationReview"]] = relationship(
        "SummarizationReview", back_populates="session_retriever", cascade="all, delete-orphan"
    )


class SummarizationReview(Base):
    __tablename__ = "summarization_reviews"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_retriever_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("session_retrievers.id"), nullable=False, index=True
    )
    context_summary: Mapped[str] = mapped_column(Text, nullable=False)
    files_analyzed: Mapped[list[str]] = mapped_column(JSON, default=list)
    writes_detected: Mapped[list[str]] = mapped_column(JSON, default=list)
    goal_achievement: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    related_sessions: Mapped[list[UUID]] = mapped_column(JSON, default=list)
    key_insights: Mapped[list[str]] = mapped_column(JSON, default=list)
    action_items: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    token_coverage: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    session_retriever: Mapped["SessionRetriever"] = relationship("SessionRetriever", back_populates="summarization_reviews")


# Vector Database Extensions (for pgvector)
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
    root_execution_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    parent_execution_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    execution_role: Mapped[str] = mapped_column(String(64), default="root_orchestrator", index=True)
    owner_execution_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
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
    state_version: Mapped[int] = mapped_column(Integer, default=1)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_event_sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_snapshot_sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_effect_sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_message_sequence: Mapped[int] = mapped_column(Integer, default=0)
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


class AgentExecutionMessage(Base):
    __tablename__ = "agent_execution_messages"
    __table_args__ = (UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_message_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_executions.id", ondelete="CASCADE"), index=True)
    root_execution_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    parent_execution_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer)
    message_type: Mapped[str] = mapped_column(String(32), index=True)
    sender_execution_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    recipient_execution_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="internal")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[dict[str, Any]] = mapped_column("payload", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentExecutionProcess(Base):
    __tablename__ = "agent_execution_processes"
    __table_args__ = (UniqueConstraint("execution_id", "process_key", name="uq_agent_execution_process_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_executions.id", ondelete="CASCADE"), index=True)
    process_key: Mapped[str] = mapped_column(String(128), index=True)
    tab_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    owner_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    terminal_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cwd: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="running", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessionRuntimeState(Base):
    __tablename__ = "session_runtime_state"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    execution_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True, index=True)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state_hash: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Research & Browser Automation Models
# ---------------------------------------------------------------------------

class BrowserActionTrail(Base):
    """Track every browser action for audit and debugging."""
    __tablename__ = "browser_action_trails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    browser_id: Mapped[str] = mapped_column(String(64), index=True)
    iteration_type: Mapped[str] = mapped_column(String(32), index=True)
    action_data: Mapped[dict] = mapped_column(JSON, default=dict)
    success: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ResearchSession(Base):
    """Track overall research sessions and their state."""
    __tablename__ = "research_sessions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32))
    complexity_level: Mapped[str] = mapped_column(String(16))
    browser_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    confidence_level: Mapped[str] = mapped_column(String(16), default="unknown")
    synthesis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    actions_completed: Mapped[int] = mapped_column(Integer, default=0)
    errors_encountered: Mapped[int] = mapped_column(Integer, default=0)
    session_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ResearchFinding(Base):
    """Store individual research findings with source classification."""
    __tablename__ = "research_findings"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    research_session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sessions.id"), nullable=False, index=True
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    trust_level: Mapped[str] = mapped_column(String(16))
    domain_authority: Mapped[float] = mapped_column(Float, default=0.0)
    content_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    extraction_method: Mapped[str] = mapped_column(String(32), default="text_extraction")
    conflicts_with: Mapped[list[str]] = mapped_column(JSON, default=list)
    browser_id: Mapped[str] = mapped_column(String(64), index=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    research_session: Mapped["ResearchSession"] = relationship("ResearchSession")


class SessionReview(Base):
    """Session review records for context governance."""
    __tablename__ = "session_reviews"
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id"), index=True)
    window_start: Mapped[int] = mapped_column(Integer)
    window_end: Mapped[int] = mapped_column(Integer)
    review_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    priority: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession")
    review_results: Mapped[list["SessionReviewResult"]] = relationship(
        "SessionReviewResult", back_populates="review", cascade="all, delete-orphan"
    )


class SessionReviewResult(Base):
    """Detailed results of session review analysis."""
    __tablename__ = "session_review_results"
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_id: Mapped[str] = mapped_column(String(64), ForeignKey("session_reviews.id"), index=True)
    result_type: Mapped[str] = mapped_column(String(32))
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    
    # Relationships
    review: Mapped["SessionReview"] = relationship("SessionReview", back_populates="review_results")


class SourceClassification(Base):
    """Cache source classifications to avoid re-classification."""
    __tablename__ = "source_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    trust_level: Mapped[str] = mapped_column(String(16))
    domain_authority: Mapped[float] = mapped_column(Float, default=0.0)
    content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    last_classified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    verified_count: Mapped[int] = mapped_column(Integer, default=0)


class BrowserInstance(Base):
    """Track browser instance lifecycle and state."""
    __tablename__ = "browser_instances"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    browser_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    instance_id: Mapped[str] = mapped_column(String(64))
    tab_id: Mapped[str] = mapped_column(String(64))
    research_session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sessions.id"), nullable=True, index=True
    )
    current_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    container_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    container_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    runtime_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    economy_mode: Mapped[str] = mapped_column(String(32), default="warm_paused")
    runtime_state: Mapped[str] = mapped_column(String(32), default="pending")
    actions_completed: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    research_session: Mapped["ResearchSession"] = relationship("ResearchSession")
