"""Memory-specific database models."""

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    session_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
