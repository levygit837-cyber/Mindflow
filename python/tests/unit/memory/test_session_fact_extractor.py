"""Unit tests for SessionFactExtractor (Phase 2, Task 2.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from mindflow_backend.memory.session.fact_extractor import SessionFactExtractor
from mindflow_backend.memory.storage.models import Base, SessionEmbedding, SessionFact


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
def fact_extractor():
    """Create a SessionFactExtractor instance."""
    return SessionFactExtractor(
        provider="vertexai",
        model="gemini-3.1-flash-lite-preview",
        max_facts=15,
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_fact_extractor_initialization():
    """Test SessionFactExtractor initializes with correct defaults."""
    extractor = SessionFactExtractor()

    assert extractor._max_facts == 15
    assert extractor._provider is not None
    assert extractor._model is not None


def test_fact_extractor_custom_config():
    """Test SessionFactExtractor with custom configuration."""
    extractor = SessionFactExtractor(
        provider="anthropic",
        model="claude-3-sonnet",
        max_facts=10,
    )

    assert extractor._provider == "anthropic"
    assert extractor._model == "claude-3-sonnet"
    assert extractor._max_facts == 10


# ============================================================================
# Message Formatting Tests
# ============================================================================


def test_format_messages_basic(fact_extractor):
    """Test basic message formatting."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]

    formatted = fact_extractor._format_messages(messages)

    assert "[1] USER: Hello" in formatted
    assert "[2] ASSISTANT: Hi there" in formatted


def test_format_messages_truncates_long_content(fact_extractor):
    """Test that very long messages are truncated."""
    long_content = "x" * 3000
    messages = [{"role": "user", "content": long_content}]

    formatted = fact_extractor._format_messages(messages)

    assert len(formatted) < len(long_content)
    assert "[truncated]" in formatted


def test_format_messages_empty_list(fact_extractor):
    """Test formatting empty message list."""
    formatted = fact_extractor._format_messages([])

    assert formatted == ""


# ============================================================================
# Fact Parsing Tests
# ============================================================================


def test_parse_facts_valid_json(fact_extractor):
    """Test parsing valid JSON response."""
    llm_response = """[
        {
            "type": "action",
            "content": "Implemented JWT authentication",
            "category": "api",
            "importance": 0.9,
            "related_files": ["api/auth.py"]
        }
    ]"""

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert len(facts) == 1
    assert facts[0].fact_type == "action"
    assert facts[0].content == "Implemented JWT authentication"
    assert facts[0].category == "api"
    assert facts[0].importance == 0.9
    assert facts[0].related_files == ["api/auth.py"]


def test_parse_facts_with_markdown_code_blocks(fact_extractor):
    """Test parsing JSON wrapped in markdown code blocks."""
    llm_response = """```json
    [
        {
            "type": "decision",
            "content": "Chose PostgreSQL over MongoDB",
            "category": "database",
            "importance": 0.8,
            "related_files": []
        }
    ]
    ```"""

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert len(facts) == 1
    assert facts[0].fact_type == "decision"


def test_parse_facts_invalid_json(fact_extractor):
    """Test parsing invalid JSON returns empty list."""
    llm_response = "This is not JSON"

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert facts == []


def test_parse_facts_not_array(fact_extractor):
    """Test parsing JSON that is not an array."""
    llm_response = '{"type": "action", "content": "test"}'

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert facts == []


def test_parse_facts_missing_required_fields(fact_extractor):
    """Test parsing facts with missing required fields."""
    llm_response = """[
        {"type": "action"},
        {"content": "Missing type"},
        {"type": "decision", "content": "Valid fact"}
    ]"""

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    # Only the valid fact should be parsed
    assert len(facts) == 1
    assert facts[0].content == "Valid fact"


def test_parse_facts_invalid_fact_type(fact_extractor):
    """Test parsing facts with invalid fact_type."""
    llm_response = """[
        {
            "type": "invalid_type",
            "content": "Should be skipped",
            "category": "api",
            "importance": 0.5,
            "related_files": []
        }
    ]"""

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert facts == []


def test_parse_facts_importance_clamping(fact_extractor):
    """Test that importance values are clamped to [0, 1]."""
    llm_response = """[
        {"type": "action", "content": "Test 1", "importance": -0.5},
        {"type": "action", "content": "Test 2", "importance": 1.5},
        {"type": "action", "content": "Test 3", "importance": 0.7}
    ]"""

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert len(facts) == 3
    assert facts[0].importance == 0.0  # Clamped from -0.5
    assert facts[1].importance == 1.0  # Clamped from 1.5
    assert facts[2].importance == 0.7  # Unchanged


def test_parse_facts_default_values(fact_extractor):
    """Test that optional fields get default values."""
    llm_response = """[
        {
            "type": "discovery",
            "content": "Found a bug"
        }
    ]"""

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert len(facts) == 1
    assert facts[0].category is None
    assert facts[0].importance == 0.5
    assert facts[0].related_files == []


# ============================================================================
# LLM Integration Tests (Mocked)
# ============================================================================


@pytest.mark.asyncio
async def test_extract_with_mock_llm(fact_extractor):
    """Test fact extraction with mocked LLM."""
    messages = [
        {"role": "user", "content": "Implement authentication"},
        {"role": "assistant", "content": "I'll implement JWT authentication"},
    ]

    mock_response = MagicMock()
    mock_response.content = """[
        {
            "type": "action",
            "content": "Implemented JWT authentication middleware",
            "category": "api",
            "importance": 0.9,
            "related_files": ["api/middleware/auth.py"]
        }
    ]"""

    with patch("mindflow_backend.memory.session.fact_extractor.get_model_for_provider") as mock_get_model:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_model.return_value = mock_llm

        facts = await fact_extractor.extract(messages, "session-1", "agent-1")

        assert len(facts) == 1
        assert facts[0].fact_type == "action"
        assert facts[0].session_id == "session-1"
        assert facts[0].agent_id == "agent-1"


@pytest.mark.asyncio
async def test_extract_empty_messages(fact_extractor):
    """Test extraction with empty message list."""
    facts = await fact_extractor.extract([], "session-1", "agent-1")

    assert facts == []


@pytest.mark.asyncio
async def test_extract_llm_failure_graceful_degradation(fact_extractor):
    """Test that LLM failure returns empty list instead of raising."""
    messages = [{"role": "user", "content": "Test"}]

    with patch("mindflow_backend.memory.session.fact_extractor.get_model_for_provider") as mock_get_model:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM API error")
        mock_get_model.return_value = mock_llm

        facts = await fact_extractor.extract(messages, "session-1", "agent-1")

        # Should return empty list, not raise
        assert facts == []


@pytest.mark.asyncio
async def test_extract_respects_max_facts_limit(fact_extractor):
    """Test that extraction respects max_facts limit."""
    messages = [{"role": "user", "content": "Test"}]

    # Create response with 20 facts
    facts_json = [
        {
            "type": "action",
            "content": f"Action {i}",
            "category": "test",
            "importance": 0.5,
            "related_files": [],
        }
        for i in range(20)
    ]

    mock_response = MagicMock()
    mock_response.content = json.dumps(facts_json)

    with patch("mindflow_backend.memory.session.fact_extractor.get_model_for_provider") as mock_get_model:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_model.return_value = mock_llm

        facts = await fact_extractor.extract(messages, "session-1", "agent-1")

        # Should be limited to max_facts (15)
        assert len(facts) == 15


# ============================================================================
# Persistence Tests
# ============================================================================


@pytest.mark.asyncio
async def test_persist_facts_without_embeddings(async_session, fact_extractor):
    """Test persisting facts without generating embeddings."""
    facts = [
        SessionFact(
            session_id="session-1",
            agent_id="agent-1",
            fact_type="action",
            content="Test fact 1",
            category="api",
            importance=0.8,
            related_files=["test.py"],
        ),
        SessionFact(
            session_id="session-1",
            agent_id="agent-1",
            fact_type="decision",
            content="Test fact 2",
            category="database",
            importance=0.7,
            related_files=[],
        ),
    ]

    count = await fact_extractor.persist_facts(
        async_session,
        facts,
        generate_embeddings=False,
    )

    assert count == 2

    # Verify facts were persisted
    result = await async_session.execute(select(SessionFact))
    saved_facts = result.scalars().all()

    assert len(saved_facts) == 2
    assert saved_facts[0].content == "Test fact 1"
    assert saved_facts[1].content == "Test fact 2"


@pytest.mark.asyncio
async def test_persist_facts_with_embeddings(async_session, fact_extractor):
    """Test persisting facts with embedding generation."""
    facts = [
        SessionFact(
            session_id="session-1",
            agent_id="agent-1",
            fact_type="discovery",
            content="Found a critical bug",
            category="tests",
            importance=0.9,
            related_files=["tests/test_auth.py"],
        ),
    ]

    # Mock embedding generation - use AsyncMock for async method
    mock_embed = AsyncMock(return_value=[0.1] * 768)

    with patch.object(fact_extractor, "_generate_embedding", mock_embed):
        count = await fact_extractor.persist_facts(
            async_session,
            facts,
            generate_embeddings=True,
        )

        assert count == 1

        # Verify fact was persisted
        fact_result = await async_session.execute(select(SessionFact))
        saved_facts = fact_result.scalars().all()
        assert len(saved_facts) == 1

        # Verify embedding was created
        embedding_result = await async_session.execute(select(SessionEmbedding))
        embeddings = embedding_result.scalars().all()
        assert len(embeddings) == 1
        assert embeddings[0].content_kind == "fact"
        assert embeddings[0].session_metadata["source_type"] == "session_fact"
        assert embeddings[0].session_metadata["fact_type"] == "discovery"

        # Verify fact is linked to embedding
        assert saved_facts[0].embedding_id == embeddings[0].id


@pytest.mark.asyncio
async def test_persist_facts_empty_list(async_session, fact_extractor):
    """Test persisting empty fact list."""
    count = await fact_extractor.persist_facts(async_session, [])

    assert count == 0


@pytest.mark.asyncio
async def test_persist_facts_embedding_failure_graceful(async_session, fact_extractor):
    """Test that embedding generation failure doesn't prevent fact persistence."""
    facts = [
        SessionFact(
            session_id="session-1",
            agent_id="agent-1",
            fact_type="error",
            content="Error occurred",
            category="api",
            importance=0.6,
            related_files=[],
        ),
    ]

    # Mock embedding generation to fail - use AsyncMock
    mock_embed = AsyncMock(side_effect=Exception("Embedding service unavailable"))

    with patch.object(fact_extractor, "_generate_embedding", mock_embed):
        count = await fact_extractor.persist_facts(
            async_session,
            facts,
            generate_embeddings=True,
        )

        # Fact should still be persisted
        assert count == 1

        # Verify fact exists
        result = await async_session.execute(select(SessionFact))
        saved_facts = result.scalars().all()
        assert len(saved_facts) == 1

        # Verify no embedding was created
        embedding_result = await async_session.execute(select(SessionEmbedding))
        embeddings = embedding_result.scalars().all()
        assert len(embeddings) == 0


# ============================================================================
# All Fact Types Tests
# ============================================================================


@pytest.mark.asyncio
async def test_all_fact_types_valid(fact_extractor):
    """Test that all valid fact types are accepted."""
    llm_response = """[
        {"type": "action", "content": "Action fact"},
        {"type": "decision", "content": "Decision fact"},
        {"type": "discovery", "content": "Discovery fact"},
        {"type": "error", "content": "Error fact"},
        {"type": "state", "content": "State fact"}
    ]"""

    facts = fact_extractor._parse_facts(llm_response, "session-1", "agent-1")

    assert len(facts) == 5
    fact_types = {f.fact_type for f in facts}
    assert fact_types == {"action", "decision", "discovery", "error", "state"}


# ============================================================================
# Integration Test: Extract + Persist
# ============================================================================


@pytest.mark.asyncio
async def test_extract_and_persist_end_to_end(async_session, fact_extractor):
    """Test complete flow: extract facts from messages and persist."""
    messages = [
        {"role": "user", "content": "Fix the authentication bug"},
        {"role": "assistant", "content": "I found the issue in auth.py and fixed it"},
    ]

    mock_response = MagicMock()
    mock_response.content = """[
        {
            "type": "action",
            "content": "Fixed authentication bug in auth.py",
            "category": "api",
            "importance": 0.9,
            "related_files": ["api/auth.py"]
        },
        {
            "type": "discovery",
            "content": "Bug was caused by incorrect token validation",
            "category": "api",
            "importance": 0.7,
            "related_files": ["api/auth.py"]
        }
    ]"""

    with patch("mindflow_backend.memory.session.fact_extractor.get_model_for_provider") as mock_get_model:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_model.return_value = mock_llm

        # Extract facts
        facts = await fact_extractor.extract(messages, "session-1", "agent-1")

        assert len(facts) == 2

        # Persist facts
        count = await fact_extractor.persist_facts(
            async_session,
            facts,
            generate_embeddings=False,
        )

        assert count == 2

        # Verify in database
        result = await async_session.execute(select(SessionFact))
        saved_facts = result.scalars().all()

        assert len(saved_facts) == 2
        assert saved_facts[0].session_id == "session-1"
        assert saved_facts[0].agent_id == "agent-1"
        assert saved_facts[0].fact_type in {"action", "discovery"}


import json
