"""Task Memory Models.

Modelos de dados para memória semântica de tasks e sub-tasks.
"""

from datetime import UTC, datetime
from uuid import uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TaskMemory(Base):
    """Memória principal de uma task."""
    __tablename__ = "task_memory"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    parent_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="active")
    priority: Mapped[float] = mapped_column(Float, default=1.0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TaskChunk(Base):
    """Chunk de conteúdo específico de uma task."""
    __tablename__ = "task_chunks"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_memory_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("task_memory.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer)
    chunk_type: Mapped[str] = mapped_column(String(32), default="content")
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskEmbedding(Base):
    """Embedding vetorial para busca semântica de tasks.

    Note: This table is being phased out. Embeddings now live in TaskChunk.embedding (Vector).
    Kept for backwards compatibility during transition.
    """
    __tablename__ = "task_embeddings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_memory_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("task_memory.id"), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("task_chunks.id"), nullable=True)
    content_type: Mapped[str] = mapped_column(String(16))  # task, chunk, summary
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskDependency(Base):
    """Dependências entre tasks."""
    __tablename__ = "task_dependencies"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    parent_task_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("task_memory.id"), nullable=False)
    child_task_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("task_memory.id"), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(32))  # requires, enables, blocks
    strength: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
