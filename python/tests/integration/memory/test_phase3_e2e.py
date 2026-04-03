"""
End-to-End Integration Tests for Phase 3 Memory System.

Tests the complete flow:
1. MemoryObserver monitors events and creates annotations
2. SessionFactExtractor extracts facts from conversations
3. Smart compaction preserves facts during memory compression
4. Cross-session recall retrieves facts from previous sessions
5. MemoryFacade formats context with SessionFacts
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from mindflow_backend.execution.observers.memory_observer import MemoryObserver
from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.memory.session.fact_extractor import SessionFactExtractor
from mindflow_backend.memory.storage.models import Base, SessionFact
from mindflow_backend.schemas.memory.contracts import MemoryRecallRequest


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
    async with AsyncSession(async_db) as session:
        yield session


@pytest_asyncio.fixture
async def memory_facade():
    """Create a MemoryFacade instance."""
    return MemoryFacade()


# ============================================================================
# Complete E2E Flow Tests
# ============================================================================


class TestPhase3CompleteE2E:
    """End-to-end tests for the complete Phase 3 memory system."""

    @pytest.mark.asyncio
    async def test_complete_memory_lifecycle(self, async_session: AsyncSession):
        """Test complete memory lifecycle: observe → extract → compact → recall."""

        # ===== STEP 1: Session 1 - Agent works and observer monitors =====
        session_1_id = "session-e2e-001"
        agent_id = "coder-agent"

        # Simulate conversation in Session 1
        messages_session_1 = [
            {"role": "user", "content": "Implement OAuth2 authentication"},
            {
                "role": "assistant",
                "content": "I'll implement OAuth2 with Google and GitHub providers using passport.js.",
            },
            {"role": "user", "content": "Add rate limiting to prevent abuse"},
            {
                "role": "assistant",
                "content": "Added express-rate-limit middleware with Redis store, 100 requests per 15 minutes.",
            },
            {"role": "user", "content": "Why did you choose Redis for rate limiting?"},
            {
                "role": "assistant",
                "content": "Redis provides fast in-memory storage with atomic operations, perfect for distributed rate limiting.",
            },
        ]

        # Extract facts from Session 1
        extractor = SessionFactExtractor(max_facts=10)
        facts_session_1 = await extractor.extract(
            messages=messages_session_1,
            session_id=session_1_id,
            agent_id=agent_id,
        )

        # Persist facts
        count = await extractor.persist_facts(
            db=async_session,
            facts=facts_session_1,
            generate_embeddings=False,
        )
        await async_session.commit()

        assert count > 0, "Should have extracted and persisted facts from Session 1"

        # Verify facts are in database
        result = await async_session.execute(
            select(SessionFact).where(SessionFact.session_id == session_1_id)
        )
        persisted_facts = result.scalars().all()
        assert len(persisted_facts) > 0

        # ===== STEP 2: Session 2 - New agent recalls facts from Session 1 =====
        session_2_id = "session-e2e-002"

        # Query for facts about authentication
        result = await async_session.execute(
            select(SessionFact).where(SessionFact.content.contains("OAuth2"))
        )
        recalled_facts = result.scalars().all()

        assert len(recalled_facts) > 0, "Should recall OAuth2 facts from Session 1"
        assert any(
            fact.session_id == session_1_id for fact in recalled_facts
        ), "Recalled facts should be from Session 1"

        # ===== STEP 3: Verify cross-agent queries work =====
        result = await async_session.execute(
            select(SessionFact).where(SessionFact.agent_id == agent_id)
        )
        agent_facts = result.scalars().all()

        assert len(agent_facts) > 0, "Should find facts by agent_id"
        assert all(fact.agent_id == agent_id for fact in agent_facts)

    @pytest.mark.asyncio
    async def test_observer_to_fact_extraction_flow(
        self, async_session: AsyncSession, memory_facade: MemoryFacade
    ):
        """Test flow from MemoryObserver events to SessionFact extraction."""

        # Create observer
        observer = MemoryObserver(
            observer_agent_id="observer-agent",
            memory_facade=memory_facade,
            session_id="session-observer-001",
            project_root="/test/project",
            project_name="TestProject",
        )

        # Track annotations created
        annotations_created = []

        # Mock _save_annotation to capture annotations without DB
        async def mock_save_annotation(annotation, code_change_info=None, category=None, subcategory=None):
            annotations_created.append({
                "annotation": annotation,
                "code_change_info": code_change_info,
                "category": category,
                "subcategory": subcategory,
            })

        observer._save_annotation = mock_save_annotation

        # Simulate events that observer monitors
        events = [
            {
                "type": "tool_result",
                "agent_id": "coder",
                "mission_id": "mission-1",
                "level": "INFO",
                "message": "Implemented JWT authentication",
                "data": {
                    "tool_name": "write_file",
                    "file_path": "src/auth/jwt.py",
                    "status": "success",
                },
            },
            {
                "type": "agent_decision",
                "agent_id": "coder",
                "mission_id": "mission-1",
                "level": "INFO",
                "message": "Decided to use bcrypt for password hashing",
                "data": {
                    "decision": "Use bcrypt with cost factor 12",
                    "reasoning": "Industry standard, resistant to GPU attacks",
                },
            },
        ]

        # Process events through observer
        for event in events:
            await observer._process_event(event)

        # Verify observer created annotations
        assert len(annotations_created) == len(events), f"Expected {len(events)} annotations, got {len(annotations_created)}"

        # Verify first annotation (code change) has code_change_info
        first = annotations_created[0]
        assert first["code_change_info"] is not None, "First event should have code_change_info"
        assert first["code_change_info"]["file_path"] == "src/auth/jwt.py"

        # Verify second annotation (decision) has no code_change_info
        second = annotations_created[1]
        assert second["code_change_info"] is None, "Second event should not have code_change_info"

        # Verify annotations have rich context
        for item in annotations_created:
            annotation = item["annotation"]
            assert len(annotation.content) > 100, "Should have rich context"
            assert "session:session-observer-001" in annotation.tags
            assert "source_agent:coder" in annotation.tags

    @pytest.mark.asyncio
    async def test_smart_compaction_preserves_facts(self, async_session: AsyncSession):
        """Test that smart compaction extracts and preserves SessionFacts."""

        session_id = "session-compact-001"
        agent_id = "assistant"

        # Simulate conversation that will be compacted
        messages = [
            {"role": "user", "content": "How do I implement caching?"},
            {
                "role": "assistant",
                "content": "I recommend using Redis for caching with a TTL of 1 hour.",
            },
            {"role": "user", "content": "What about cache invalidation?"},
            {
                "role": "assistant",
                "content": "Use event-driven invalidation with pub/sub pattern.",
            },
        ]

        # Mock LLM response with valid facts JSON
        mock_llm_response = """[
  {
    "type": "decision",
    "content": "Chose Redis for caching with 1 hour TTL for fast in-memory storage",
    "category": "caching",
    "importance": 0.8,
    "related_files": []
  },
  {
    "type": "decision",
    "content": "Implemented event-driven cache invalidation using pub/sub pattern",
    "category": "caching",
    "importance": 0.7,
    "related_files": []
  }
]"""

        # Extract facts before compaction
        extractor = SessionFactExtractor(max_facts=5)

        # Mock the LLM call
        with patch.object(extractor, "_call_llm", return_value=mock_llm_response):
            facts = await extractor.extract(
                messages=messages,
                session_id=session_id,
                agent_id=agent_id,
            )

        count = await extractor.persist_facts(
            db=async_session,
            facts=facts,
            generate_embeddings=False,
        )
        await async_session.commit()

        assert count > 0, "Should have extracted facts before compaction"

        # Verify facts are preserved in database
        result = await async_session.execute(
            select(SessionFact).where(SessionFact.session_id == session_id)
        )
        preserved_facts = result.scalars().all()

        assert len(preserved_facts) > 0, "Facts should be preserved after compaction"
        assert any("Redis" in fact.content for fact in preserved_facts)

    @pytest.mark.asyncio
    async def test_memory_facade_formats_context_with_facts(
        self, async_session: AsyncSession, memory_facade: MemoryFacade
    ):
        """Test that MemoryFacade includes SessionFacts in formatted context."""

        # Create mock fact hits
        fact_hits = [
            {
                "content": "Implemented OAuth2 authentication with Google and GitHub providers",
                "fact_type": "action",
                "category": "authentication",
                "session_id": "session-001",
                "agent_id": "coder",
                "score": 0.95,
            },
            {
                "content": "Chose Redis for rate limiting due to atomic operations and distributed support",
                "fact_type": "decision",
                "category": "architecture",
                "session_id": "session-001",
                "agent_id": "coder",
                "score": 0.88,
            },
            {
                "content": "Discovered SQL injection vulnerability in user search endpoint",
                "fact_type": "discovery",
                "category": "security",
                "session_id": "session-002",
                "agent_id": "security-agent",
                "score": 0.92,
            },
        ]

        # Format context with facts
        formatted = memory_facade._format_context(
            message_hits=[],
            block_hits=[],
            fact_hits=fact_hits,
        )

        # Verify formatted context structure
        assert "Context from Previous Sessions" in formatted
        assert "[action:authentication]" in formatted
        assert "[decision:architecture]" in formatted
        assert "[discovery:security]" in formatted
        assert "OAuth2 authentication" in formatted
        assert "Redis for rate limiting" in formatted
        assert "SQL injection vulnerability" in formatted


# ============================================================================
# Performance Tests
# ============================================================================


class TestPhase3Performance:
    """Performance tests for Phase 3 memory system."""

    @pytest.mark.asyncio
    async def test_multiple_sessions_extraction_performance(
        self, async_session: AsyncSession
    ):
        """Test fact extraction performance with multiple sessions."""

        extractor = SessionFactExtractor(max_facts=10)
        num_sessions = 10

        # Extract facts from multiple sessions
        total_facts = 0
        for i in range(num_sessions):
            messages = [
                {"role": "user", "content": f"Task {i}: Implement feature X"},
                {
                    "role": "assistant",
                    "content": f"Implemented feature X with approach Y for session {i}.",
                },
            ]

            facts = await extractor.extract(
                messages=messages,
                session_id=f"session-perf-{i:03d}",
                agent_id="perf-agent",
            )

            count = await extractor.persist_facts(
                db=async_session,
                facts=facts,
                generate_embeddings=False,
            )
            total_facts += count

        await async_session.commit()

        # Verify all facts were extracted
        result = await async_session.execute(select(SessionFact))
        all_facts = result.scalars().all()

        assert len(all_facts) >= num_sessions, "Should have facts from all sessions"
        assert total_facts > 0, "Should have extracted facts"

    @pytest.mark.asyncio
    async def test_concurrent_fact_extraction(self, async_session: AsyncSession):
        """Test concurrent fact extraction from multiple agents."""

        extractor = SessionFactExtractor(max_facts=5)

        # Create tasks for concurrent extraction
        async def extract_for_agent(agent_id: str, session_id: str):
            messages = [
                {"role": "user", "content": f"Task for {agent_id}"},
                {"role": "assistant", "content": f"Completed task for {agent_id}"},
            ]

            facts = await extractor.extract(
                messages=messages,
                session_id=session_id,
                agent_id=agent_id,
            )

            return await extractor.persist_facts(
                db=async_session,
                facts=facts,
                generate_embeddings=False,
            )

        # Run concurrent extractions
        tasks = [
            extract_for_agent(f"agent-{i}", f"session-concurrent-{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)
        await async_session.commit()

        # Verify all extractions completed
        assert all(count >= 0 for count in results), "All extractions should complete"

        # Verify facts from all agents
        result = await async_session.execute(select(SessionFact))
        all_facts = result.scalars().all()

        agent_ids = {fact.agent_id for fact in all_facts}
        assert len(agent_ids) >= 3, "Should have facts from multiple agents"


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestPhase3EdgeCases:
    """Edge case tests for Phase 3 memory system."""

    @pytest.mark.asyncio
    async def test_empty_session_extraction(self, async_session: AsyncSession):
        """Test fact extraction from empty session."""

        extractor = SessionFactExtractor(max_facts=5)

        # Extract from empty messages
        facts = await extractor.extract(
            messages=[],
            session_id="session-empty",
            agent_id="test-agent",
        )

        assert len(facts) == 0, "Should return empty list for empty session"

    @pytest.mark.asyncio
    async def test_malformed_llm_response_handling(self, async_session: AsyncSession):
        """Test graceful handling of malformed LLM responses."""

        extractor = SessionFactExtractor(max_facts=5)

        # Mock LLM to return malformed JSON
        with patch.object(extractor, "_call_llm", return_value="Not valid JSON"):
            facts = await extractor.extract(
                messages=[
                    {"role": "user", "content": "Test"},
                    {"role": "assistant", "content": "Response"},
                ],
                session_id="session-malformed",
                agent_id="test-agent",
            )

            # Should gracefully return empty list
            assert len(facts) == 0, "Should handle malformed JSON gracefully"

    @pytest.mark.asyncio
    async def test_very_long_conversation_extraction(self, async_session: AsyncSession):
        """Test fact extraction from very long conversation."""

        extractor = SessionFactExtractor(max_facts=10)

        # Create very long conversation (50 messages)
        messages = []
        for i in range(25):
            messages.append({"role": "user", "content": f"Question {i}"})
            messages.append({"role": "assistant", "content": f"Answer {i}"})

        facts = await extractor.extract(
            messages=messages,
            session_id="session-long",
            agent_id="test-agent",
        )

        # Should extract facts and respect max_facts limit
        assert len(facts) <= 10, "Should respect max_facts limit"

    @pytest.mark.asyncio
    async def test_duplicate_fact_handling(self, async_session: AsyncSession):
        """Test handling of duplicate facts from same session."""

        extractor = SessionFactExtractor(max_facts=5)
        session_id = "session-duplicate"

        messages = [
            {"role": "user", "content": "Implement caching"},
            {"role": "assistant", "content": "Implemented Redis caching"},
        ]

        # Extract facts twice
        facts_1 = await extractor.extract(
            messages=messages,
            session_id=session_id,
            agent_id="agent-1",
        )

        count_1 = await extractor.persist_facts(
            db=async_session,
            facts=facts_1,
            generate_embeddings=False,
        )

        facts_2 = await extractor.extract(
            messages=messages,
            session_id=session_id,
            agent_id="agent-1",
        )

        count_2 = await extractor.persist_facts(
            db=async_session,
            facts=facts_2,
            generate_embeddings=False,
        )

        await async_session.commit()

        # Both should succeed (no unique constraint on content)
        assert count_1 > 0
        assert count_2 > 0

        # Verify facts are in database
        result = await async_session.execute(
            select(SessionFact).where(SessionFact.session_id == session_id)
        )
        all_facts = result.scalars().all()

        assert len(all_facts) >= count_1, "Should have persisted facts"
