from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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
    tokens_since_chunk: Mapped[int] = mapped_column(Integer, default=0)
    last_chunked_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_sequence: Mapped[int] = mapped_column(Integer, default=0)
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
    vector: Mapped[list[float]] = mapped_column(JSON, default=list)
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

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    session_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


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
    actions_completed: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    research_session: Mapped["ResearchSession"] = relationship("ResearchSession")
