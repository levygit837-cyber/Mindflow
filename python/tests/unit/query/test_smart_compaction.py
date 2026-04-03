"""Unit tests for Smart Compaction with SessionFact extraction (Phase 2, Task 2.2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from mindflow_backend.memory.storage.models import Base, SessionFact
from mindflow_backend.query.budget.auto_compact import (
    AutoCompactService,
    CompactConfig,
    CompactStrategy,
)


@pytest_asyncio.fixture
async def async_db():
    """Create an async in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


@pytest_asyncio.fixture
async def async_session(async_db):
    """Create an async database session for testing."""
    async with AsyncSession(async_db, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
def compact_service():
    """Create AutoCompactService instance."""
    config = CompactConfig(
        max_context_tokens=100_000,
        enable_snip=True,
        enable_context_collapse=True,
        enable_llm_summary=True,
        enable_cache_compact=False,
    )
    return AutoCompactService(config)


# ============================================================================
# Helper Method Tests
# ============================================================================


def test_extract_session_id_from_metadata(compact_service):
    """Test extracting session_id from message metadata."""
    messages = [
        {
            "role": "user",
            "content": "Hello",
            "metadata": {"session_id": "session-123"},
        }
    ]

    session_id = compact_service._extract_session_id(messages)
    assert session_id == "session-123"


def test_extract_session_id_from_top_level(compact_service):
    """Test extracting session_id from top-level message field."""
    messages = [
        {
            "role": "user",
            "content": "Hello",
            "session_id": "session-456",
        }
    ]

    session_id = compact_service._extract_session_id(messages)
    assert session_id == "session-456"


def test_extract_session_id_fallback(compact_service):
    """Test session_id fallback when not found in messages."""
    messages = [
        {"role": "user", "content": "Hello"},
    ]

    session_id = compact_service._extract_session_id(messages)

    # Should generate a fallback ID
    assert session_id is not None
    assert len(session_id) == 16  # MD5 hash truncated to 16 chars


def test_extract_agent_id_from_metadata(compact_service):
    """Test extracting agent_id from message metadata."""
    messages = [
        {
            "role": "assistant",
            "content": "Response",
            "metadata": {"agent_id": "agent-coder"},
        }
    ]

    agent_id = compact_service._extract_agent_id(messages)
    assert agent_id == "agent-coder"


def test_extract_agent_id_from_name(compact_service):
    """Test extracting agent_id from assistant name field."""
    messages = [
        {
            "role": "assistant",
            "content": "Response",
            "name": "coder-agent",
        }
    ]

    agent_id = compact_service._extract_agent_id(messages)
    assert agent_id == "coder-agent"


def test_extract_agent_id_fallback(compact_service):
    """Test agent_id fallback when not found."""
    messages = [
        {"role": "user", "content": "Hello"},
    ]

    agent_id = compact_service._extract_agent_id(messages)
    assert agent_id == "compaction"


# ============================================================================
# Smart Compaction Tests (Mocked)
# ============================================================================


@pytest.mark.asyncio
async def test_summary_compact_with_fact_extraction(compact_service):
    """Test that summary compaction extracts and persists facts."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Implement authentication", "session_id": "session-1"},
        {"role": "assistant", "content": "I'll implement JWT auth", "agent_id": "coder"},
        {"role": "user", "content": "Add tests"},
        {"role": "assistant", "content": "Tests added"},
    ]

    # Mock LLM summarize function
    async def mock_summarize(msgs):
        return "User requested authentication implementation. JWT auth was implemented and tests were added."

    # Mock fact extractor
    mock_facts = [
        MagicMock(
            session_id="session-1",
            agent_id="coder",
            fact_type="action",
            content="Implemented JWT authentication",
            category="api",
            importance=0.9,
        )
    ]

    with patch("mindflow_backend.memory.session.fact_extractor.SessionFactExtractor") as MockExtractor:
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = mock_facts
        mock_extractor.persist_facts.return_value = 1
        MockExtractor.return_value = mock_extractor

        with patch("mindflow_backend.infra.database.connection.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_db.return_value = mock_session

            result = await compact_service._summary_compact(
                messages,
                current_tokens=50_000,
                llm_summarize_fn=mock_summarize,
            )

            # Verify compaction succeeded
            assert result.success is True
            assert result.strategy_used == CompactStrategy.SUMMARY
            assert result.tokens_saved > 0

            # Verify fact extraction was called
            mock_extractor.extract.assert_called_once()
            mock_extractor.persist_facts.assert_called_once()

            # Verify compacted messages include fact preservation notice
            summary_msg = next(
                (m for m in result.compacted_messages if m.get("is_compact_summary")),
                None
            )
            assert summary_msg is not None
            assert "1 facts preserved" in summary_msg["content"]


@pytest.mark.asyncio
async def test_summary_compact_fact_extraction_failure_graceful(compact_service):
    """Test that compaction continues even if fact extraction fails."""
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Test message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Test message 2"},
        {"role": "assistant", "content": "Response 2"},
    ]

    async def mock_summarize(msgs):
        return "Conversation summary"

    # Mock fact extractor to raise exception
    with patch("mindflow_backend.memory.session.fact_extractor.SessionFactExtractor") as MockExtractor:
        mock_extractor = AsyncMock()
        mock_extractor.extract.side_effect = Exception("Fact extraction failed")
        MockExtractor.return_value = mock_extractor

        result = await compact_service._summary_compact(
            messages,
            current_tokens=50_000,
            llm_summarize_fn=mock_summarize,
        )

        # Compaction should still succeed
        assert result.success is True
        assert result.strategy_used == CompactStrategy.SUMMARY


@pytest.mark.asyncio
async def test_summary_compact_llm_failure_fallback_to_snip(compact_service):
    """Test that compaction falls back to snip when LLM fails."""
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Response 2"},
    ]

    # Mock LLM to return None (failure)
    async def mock_summarize_fail(msgs):
        return None

    result = await compact_service._summary_compact(
        messages,
        current_tokens=50_000,
        llm_summarize_fn=mock_summarize_fail,
    )

    # Should fallback to snip
    assert result.success is True
    assert result.strategy_used == CompactStrategy.SNIP


@pytest.mark.asyncio
async def test_summary_compact_preserves_system_messages(compact_service):
    """Test that system messages are always preserved."""
    messages = [
        {"role": "system", "content": "System prompt 1"},
        {"role": "system", "content": "System prompt 2"},
        {"role": "user", "content": "User message 1"},
        {"role": "assistant", "content": "Assistant response 1"},
        {"role": "user", "content": "User message 2"},
        {"role": "assistant", "content": "Assistant response 2"},
    ]

    async def mock_summarize(msgs):
        return "Summary"

    with patch("mindflow_backend.memory.session.fact_extractor.SessionFactExtractor") as MockExtractor:
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = []
        MockExtractor.return_value = mock_extractor

        result = await compact_service._summary_compact(
            messages,
            current_tokens=50_000,
            llm_summarize_fn=mock_summarize,
        )

        # Count system messages in result
        system_msgs = [m for m in result.compacted_messages if m.get("role") == "system"]
        assert len(system_msgs) == 2


@pytest.mark.asyncio
async def test_summary_compact_keeps_recent_messages(compact_service):
    """Test that recent messages are preserved."""
    messages = [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Old message 1"},
        {"role": "assistant", "content": "Old response 1"},
        {"role": "user", "content": "Old message 2"},
        {"role": "assistant", "content": "Old response 2"},
        {"role": "user", "content": "Recent message 1"},
        {"role": "assistant", "content": "Recent response 1"},
        {"role": "user", "content": "Recent message 2"},
        {"role": "assistant", "content": "Recent response 2"},
        {"role": "user", "content": "Most recent"},
    ]

    async def mock_summarize(msgs):
        return "Summary of old messages"

    with patch("mindflow_backend.memory.session.fact_extractor.SessionFactExtractor") as MockExtractor:
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = []
        MockExtractor.return_value = mock_extractor

        result = await compact_service._summary_compact(
            messages,
            current_tokens=50_000,
            llm_summarize_fn=mock_summarize,
        )

        # Should have: system + summary + 5 recent messages
        conversation_msgs = [m for m in messages if m.get("role") != "system"]
        recent_count = min(5, len(conversation_msgs))

        # Verify recent messages are in result
        assert "Most recent" in str(result.compacted_messages)
        assert "Recent message 2" in str(result.compacted_messages)


@pytest.mark.asyncio
async def test_summary_compact_not_enough_messages(compact_service):
    """Test that compaction fails gracefully with too few messages."""
    messages = [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Only message"},
    ]

    async def mock_summarize(msgs):
        return "Summary"

    result = await compact_service._summary_compact(
        messages,
        current_tokens=50_000,
        llm_summarize_fn=mock_summarize,
    )

    assert result.success is False
    assert "Not enough messages" in result.error


# ============================================================================
# Integration Test: Extract + Persist + Compact
# ============================================================================


@pytest.mark.asyncio
async def test_smart_compaction_end_to_end(async_session, compact_service):
    """Test complete smart compaction flow with fact persistence."""
    messages = [
        {"role": "system", "content": "You are a coding assistant"},
        {
            "role": "user",
            "content": "Fix the authentication bug",
            "session_id": "session-e2e",
            "metadata": {"session_id": "session-e2e"},
        },
        {
            "role": "assistant",
            "content": "I found the bug in auth.py and fixed it",
            "agent_id": "coder",
            "metadata": {"agent_id": "coder"},
        },
        {"role": "user", "content": "Add tests for the fix"},
        {"role": "assistant", "content": "Tests added in test_auth.py"},
    ]

    async def mock_summarize(msgs):
        return "Fixed authentication bug and added tests"

    # Mock fact extractor with real-looking facts
    from mindflow_backend.memory.storage.models import SessionFact

    mock_facts = [
        SessionFact(
            session_id="session-e2e",
            agent_id="coder",
            fact_type="action",
            content="Fixed authentication bug in auth.py",
            category="api",
            importance=0.9,
            related_files=["auth.py"],
        ),
        SessionFact(
            session_id="session-e2e",
            agent_id="coder",
            fact_type="action",
            content="Added tests in test_auth.py",
            category="tests",
            importance=0.7,
            related_files=["test_auth.py"],
        ),
    ]

    with patch("mindflow_backend.memory.session.fact_extractor.SessionFactExtractor") as MockExtractor:
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = mock_facts

        # Mock persist_facts to actually save to our test database
        async def mock_persist(db, facts, generate_embeddings=True):
            for fact in facts:
                db.add(fact)
            await db.commit()
            return len(facts)

        mock_extractor.persist_facts = mock_persist
        MockExtractor.return_value = mock_extractor

        with patch("mindflow_backend.infra.database.connection.get_db_session") as mock_db:
            mock_db.return_value.__aenter__.return_value = async_session
            mock_db.return_value.__aexit__.return_value = None

            result = await compact_service._summary_compact(
                messages,
                current_tokens=50_000,
                llm_summarize_fn=mock_summarize,
            )

            # Verify compaction succeeded
            assert result.success is True
            assert result.tokens_saved > 0

            # Verify facts were persisted to database
            fact_result = await async_session.execute(select(SessionFact))
            saved_facts = fact_result.scalars().all()

            assert len(saved_facts) == 2
            assert saved_facts[0].session_id == "session-e2e"
            assert saved_facts[0].agent_id == "coder"
            assert saved_facts[0].fact_type == "action"
