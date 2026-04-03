"""Unit tests for SessionFact model (Phase 2 - Memory Session)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from mindflow_backend.memory.storage.models import (
    AgentMemoryWindow,
    Base,
    SessionEmbedding,
    SessionFact,
)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_db):
    """Create a database session for testing."""
    with Session(in_memory_db) as session:
        yield session


# ============================================================================
# SessionFact Basic CRUD Tests
# ============================================================================


def test_create_session_fact(db_session: Session):
    """Test creating a SessionFact record."""
    fact = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Implemented JWT authentication middleware",
        category="api",
        importance=0.8,
        related_files=["python/mindflow_backend/api/middleware/auth.py"],
    )
    db_session.add(fact)
    db_session.commit()

    assert fact.id is not None
    assert fact.session_id == "session-123"
    assert fact.agent_id == "coder"
    assert fact.fact_type == "action"
    assert fact.content == "Implemented JWT authentication middleware"
    assert fact.category == "api"
    assert fact.importance == 0.8
    assert fact.related_files == ["python/mindflow_backend/api/middleware/auth.py"]
    assert fact.created_at is not None


def test_session_fact_minimal_fields(db_session: Session):
    """Test creating SessionFact with only required fields."""
    fact = SessionFact(
        session_id="session-456",
        agent_id="analyst",
        fact_type="discovery",
        content="Found performance bottleneck in query execution",
    )
    db_session.add(fact)
    db_session.commit()

    assert fact.id is not None
    assert fact.category is None
    assert fact.importance == 0.5  # default value
    assert fact.related_files == []  # default empty list
    assert fact.embedding_id is None
    assert fact.source_window_id is None


def test_session_fact_timestamps(db_session: Session):
    """Test that created_at timestamp is set correctly."""
    fact = SessionFact(
        session_id="session-789",
        agent_id="coder",
        fact_type="state",
        content="Work paused at database migration step",
    )
    db_session.add(fact)
    db_session.commit()

    assert isinstance(fact.created_at, datetime)


# ============================================================================
# SessionFact Fact Types Tests
# ============================================================================


def test_session_fact_types(db_session: Session):
    """Test all valid fact types."""
    fact_types = ["action", "decision", "discovery", "error", "state"]

    for fact_type in fact_types:
        fact = SessionFact(
            session_id=f"session-{fact_type}",
            agent_id="coder",
            fact_type=fact_type,
            content=f"Test {fact_type} fact",
        )
        db_session.add(fact)

    db_session.commit()

    # Verify all were created
    results = db_session.execute(select(SessionFact)).scalars().all()
    assert len(results) == len(fact_types)


# ============================================================================
# SessionFact Foreign Key Tests
# ============================================================================


def test_session_fact_with_embedding(db_session: Session):
    """Test SessionFact with foreign key to SessionEmbedding."""
    # Create a SessionEmbedding first
    embedding = SessionEmbedding(
        session_id="session-123",
        content="Test content for embedding",
        embedding=[0.1] * 768,  # 768-dimensional vector
    )
    db_session.add(embedding)
    db_session.commit()

    # Create SessionFact linked to embedding
    fact = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Implemented feature X",
        embedding_id=embedding.id,
    )
    db_session.add(fact)
    db_session.commit()

    assert fact.embedding_id == embedding.id


def test_session_fact_with_source_window(db_session: Session):
    """Test SessionFact with foreign key to AgentMemoryWindow."""
    # Create an AgentMemoryWindow first
    window = AgentMemoryWindow(
        session_id="session-456",
        agent_id="coder",
        window_index=0,
        token_start=0,
        token_end=1000,
        event_start_id=1,
        event_end_id=10,
        summary_md="Window summary",
        key_points=["point1", "point2"],
        checksum="abc123",
    )
    db_session.add(window)
    db_session.commit()

    # Create SessionFact linked to window
    fact = SessionFact(
        session_id="session-456",
        agent_id="coder",
        fact_type="discovery",
        content="Found issue in window 0",
        source_window_id=window.id,
    )
    db_session.add(fact)
    db_session.commit()

    assert fact.source_window_id == window.id


def test_session_fact_embedding_set_null_on_delete(db_session: Session):
    """Test that deleting embedding sets embedding_id to NULL."""
    embedding = SessionEmbedding(
        session_id="session-789",
        content="Test content",
        embedding=[0.1] * 768,
    )
    db_session.add(embedding)
    db_session.commit()

    fact = SessionFact(
        session_id="session-789",
        agent_id="coder",
        fact_type="action",
        content="Test fact",
        embedding_id=embedding.id,
    )
    db_session.add(fact)
    db_session.commit()

    fact_id = fact.id

    # Delete embedding
    db_session.delete(embedding)
    db_session.commit()

    # Fact should still exist with embedding_id = NULL
    result = db_session.execute(
        select(SessionFact).where(SessionFact.id == fact_id)
    ).scalar_one()

    assert result is not None
    assert result.embedding_id is None


# ============================================================================
# SessionFact Query Tests
# ============================================================================


def test_query_facts_by_session(db_session: Session):
    """Test querying facts by session_id."""
    fact1 = SessionFact(
        session_id="session-A",
        agent_id="coder",
        fact_type="action",
        content="Fact A1",
    )
    fact2 = SessionFact(
        session_id="session-A",
        agent_id="analyst",
        fact_type="discovery",
        content="Fact A2",
    )
    fact3 = SessionFact(
        session_id="session-B",
        agent_id="coder",
        fact_type="action",
        content="Fact B1",
    )
    db_session.add_all([fact1, fact2, fact3])
    db_session.commit()

    results = db_session.execute(
        select(SessionFact).where(SessionFact.session_id == "session-A")
    ).scalars().all()

    assert len(results) == 2
    assert all(f.session_id == "session-A" for f in results)


def test_query_facts_by_category(db_session: Session):
    """Test querying facts by category."""
    fact1 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="API change",
        category="api",
    )
    fact2 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Database change",
        category="database",
    )
    fact3 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Another API change",
        category="api",
    )
    db_session.add_all([fact1, fact2, fact3])
    db_session.commit()

    results = db_session.execute(
        select(SessionFact).where(SessionFact.category == "api")
    ).scalars().all()

    assert len(results) == 2
    assert all(f.category == "api" for f in results)


def test_query_facts_by_importance(db_session: Session):
    """Test querying facts by importance threshold."""
    fact1 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Low importance",
        importance=0.3,
    )
    fact2 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="High importance",
        importance=0.9,
    )
    fact3 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Medium importance",
        importance=0.6,
    )
    db_session.add_all([fact1, fact2, fact3])
    db_session.commit()

    # Query facts with importance >= 0.7
    results = db_session.execute(
        select(SessionFact).where(SessionFact.importance >= 0.7)
    ).scalars().all()

    assert len(results) == 1
    assert results[0].content == "High importance"


def test_query_facts_by_fact_type(db_session: Session):
    """Test querying facts by fact_type."""
    fact1 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Action fact",
    )
    fact2 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="error",
        content="Error fact",
    )
    fact3 = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Another action",
    )
    db_session.add_all([fact1, fact2, fact3])
    db_session.commit()

    results = db_session.execute(
        select(SessionFact).where(SessionFact.fact_type == "action")
    ).scalars().all()

    assert len(results) == 2
    assert all(f.fact_type == "action" for f in results)


def test_composite_query_session_category_importance(db_session: Session):
    """Test composite query using session_id, category, and importance."""
    facts = [
        SessionFact(
            session_id="session-A",
            agent_id="coder",
            fact_type="action",
            content="API high",
            category="api",
            importance=0.9,
        ),
        SessionFact(
            session_id="session-A",
            agent_id="coder",
            fact_type="action",
            content="API low",
            category="api",
            importance=0.3,
        ),
        SessionFact(
            session_id="session-A",
            agent_id="coder",
            fact_type="action",
            content="DB high",
            category="database",
            importance=0.8,
        ),
        SessionFact(
            session_id="session-B",
            agent_id="coder",
            fact_type="action",
            content="API high other session",
            category="api",
            importance=0.9,
        ),
    ]
    db_session.add_all(facts)
    db_session.commit()

    # Query: session-A, category=api, importance >= 0.7
    results = db_session.execute(
        select(SessionFact)
        .where(SessionFact.session_id == "session-A")
        .where(SessionFact.category == "api")
        .where(SessionFact.importance >= 0.7)
    ).scalars().all()

    assert len(results) == 1
    assert results[0].content == "API high"


# ============================================================================
# SessionFact JSON Field Tests
# ============================================================================


def test_session_fact_related_files_json(db_session: Session):
    """Test that related_files JSON field works correctly."""
    fact = SessionFact(
        session_id="session-123",
        agent_id="coder",
        fact_type="action",
        content="Modified multiple files",
        related_files=[
            "python/mindflow_backend/api/v1/chat.py",
            "python/mindflow_backend/api/v1/sessions.py",
            "python/tests/api/test_chat.py",
        ],
    )
    db_session.add(fact)
    db_session.commit()

    # Retrieve and verify JSON field
    result = db_session.execute(
        select(SessionFact).where(SessionFact.id == fact.id)
    ).scalar_one()

    assert len(result.related_files) == 3
    assert "python/mindflow_backend/api/v1/chat.py" in result.related_files
    assert "python/tests/api/test_chat.py" in result.related_files


def test_session_fact_empty_related_files(db_session: Session):
    """Test that related_files defaults to empty list."""
    fact = SessionFact(
        session_id="session-456",
        agent_id="coder",
        fact_type="decision",
        content="Decided to use PostgreSQL",
    )
    db_session.add(fact)
    db_session.commit()

    result = db_session.execute(
        select(SessionFact).where(SessionFact.id == fact.id)
    ).scalar_one()

    assert result.related_files == []
