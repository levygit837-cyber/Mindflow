"""Tests for session chunks functionality."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from omnimind_backend.infra.config import get_settings
from omnimind_backend.memory.service import AgentMemoryService
from omnimind_backend.storage.models import (
    AgentMemoryCursor,
    AgentMemoryEvent,
    SessionChunk,
    AgentMemoryEmbedding,
    Base,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(engine)


@pytest.fixture
def memory_service():
    """Create a memory service instance for testing."""
    return AgentMemoryService()


class TestSessionChunksFlagGating:
    """Test that session chunks functionality respects feature flags."""

    def test_chunk_processing_disabled_when_flag_false(self, test_db, memory_service):
        """Test that no chunks are created when enable_session_chunks=False."""
        # Setup
        session_id = "test_session"
        agent_id = "test_agent"
        
        # Record multiple messages that would exceed chunk threshold
        for i in range(10):
            memory_service.record_message(
                test_db,
                session_id=session_id,
                agent_id=agent_id,
                role="user",
                content="This is a long message " * 100,  # ~400 tokens each
            )
        
        test_db.commit()
        
        # Verify no chunks were created
        chunks = test_db.query(SessionChunk).all()
        assert len(chunks) == 0
        
        # Verify cursor was not updated for chunking
        cursor = test_db.query(AgentMemoryCursor).filter(
            AgentMemoryCursor.session_id == session_id,
            AgentMemoryCursor.agent_id == agent_id,
        ).first()
        assert cursor is not None
        assert cursor.tokens_since_chunk == 0
        assert cursor.chunk_sequence == 0
        assert cursor.last_chunked_event_id is None

    @patch('omnimind_backend.infra.config.get_settings')
    def test_chunk_processing_enabled_when_flag_true(self, mock_settings, test_db, memory_service):
        """Test that chunks are processed when enable_session_chunks=True."""
        # Mock settings to enable session chunks
        mock_settings.return_value = Mock(
            enable_session_chunks=True,
            chunk_target_tokens=1000,
            default_provider="test_provider",
            default_model="test_model",
        )
        
        session_id = "test_session"
        agent_id = "test_agent"
        
        # Record messages that would exceed chunk threshold
        for i in range(5):
            memory_service.record_message(
                test_db,
                session_id=session_id,
                agent_id=agent_id,
                role="user",
                content="This is a message " * 200,  # ~800 tokens each
            )
        
        test_db.commit()
        
        # Verify cursor was updated for chunking
        cursor = test_db.query(AgentMemoryCursor).filter(
            AgentMemoryCursor.session_id == session_id,
            AgentMemoryCursor.agent_id == agent_id,
        ).first()
        assert cursor is not None
        assert cursor.tokens_since_chunk >= 0  # Should be reset after chunking
        assert cursor.chunk_sequence >= 0  # Should be incremented


class TestSessionChunkCreation:
    """Test session chunk creation and processing."""

    @patch('omnimind_backend.infra.config.get_settings')
    @patch('omnimind_backend.llm.providers.get_model_for_provider')
    @patch('omnimind_backend.agents.core.personalities.ANALYST_SUB_PERSONALITIES')
    def test_chunk_creation_with_valid_llm_response(
        self, mock_personalities, mock_get_model, mock_settings, test_db, memory_service
    ):
        """Test successful chunk creation with valid LLM response."""
        # Mock settings and dependencies
        mock_settings.return_value = Mock(
            enable_session_chunks=True,
            chunk_target_tokens=1000,
            default_provider="test_provider",
            default_model="test_model",
        )
        
        mock_personalities.return_value = {
            "critic": "You are a critical analyst. Analyze conversation chunks thoroughly."
        }
        
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = """SUMMARY: Users discussed project requirements and timeline
CHUNK_TYPE: discussion
TOPIC_TAGS: requirements, timeline, project
CONFIDENCE: 0.85"""
        mock_llm.invoke.return_value = mock_response
        mock_get_model.return_value = mock_llm
        
        session_id = "test_session"
        agent_id = "test_agent"
        
        # Create cursor and events manually to test chunk processing
        cursor = AgentMemoryCursor(
            session_id=session_id,
            agent_id=agent_id,
            token_total=2000,
            tokens_since_summary=1000,
            tokens_since_chunk=1500,  # Exceeds threshold
            chunk_sequence=0,
            last_chunked_event_id=None,
        )
        test_db.add(cursor)
        
        # Create some events
        for i in range(3):
            event = AgentMemoryEvent(
                session_id=session_id,
                agent_id=agent_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}: " + "test content " * 50,
                token_count=500,
            )
            test_db.add(event)
        
        test_db.commit()
        
        # Process chunk
        memory_service._process_session_chunk(
            test_db,
            session_id=session_id,
            agent_id=agent_id,
            cursor=cursor,
            event_end_id=event.id,
        )
        test_db.commit()
        
        # Verify chunk was created
        chunks = test_db.query(SessionChunk).all()
        assert len(chunks) == 1
        
        chunk = chunks[0]
        assert chunk.session_id == session_id
        assert chunk.agent_id == agent_id
        assert chunk.sequence == 1
        assert chunk.chunk_type == "discussion"
        assert "Users discussed project requirements" in chunk.content_summary
        assert chunk.topic_tags == ["requirements", "timeline", "project"]
        assert chunk.token_count == 1500  # Sum of event token counts
        assert chunk.confidence == 0.85
        
        # Verify cursor was updated
        test_db.refresh(cursor)
        assert cursor.chunk_sequence == 1
        assert cursor.tokens_since_chunk == 0
        assert cursor.last_chunked_event_id == event.id
        
        # Verify embedding was created
        embeddings = test_db.query(AgentMemoryEmbedding).filter(
            AgentMemoryEmbedding.source_type == "chunk",
            AgentMemoryEmbedding.source_id == chunk.id,
        ).all()
        assert len(embeddings) == 1

    @patch('omnimind_backend.infra.config.get_settings')
    @patch('omnimind_backend.llm.providers.get_model_for_provider')
    @patch('omnimind_backend.agents.core.personalities.ANALYST_SUB_PERSONALITIES')
    def test_chunk_creation_with_fallback_parsing(
        self, mock_personalities, mock_get_model, mock_settings, test_db, memory_service
    ):
        """Test chunk creation with fallback parsing when LLM response is malformed."""
        # Mock settings and dependencies
        mock_settings.return_value = Mock(
            enable_session_chunks=True,
            chunk_target_tokens=1000,
            default_provider="test_provider",
            default_model="test_model",
        )
        
        mock_personalities.return_value = {
            "critic": "You are a critical analyst."
        }
        
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Malformed response without proper structure"
        mock_llm.invoke.return_value = mock_response
        mock_get_model.return_value = mock_llm
        
        session_id = "test_session"
        agent_id = "test_agent"
        
        # Create cursor and events
        cursor = AgentMemoryCursor(
            session_id=session_id,
            agent_id=agent_id,
            token_total=2000,
            tokens_since_summary=1000,
            tokens_since_chunk=1500,
            chunk_sequence=0,
            last_chunked_event_id=None,
        )
        test_db.add(cursor)
        
        event = AgentMemoryEvent(
            session_id=session_id,
            agent_id=agent_id,
            role="user",
            content="Test message " * 100,
            token_count=500,
        )
        test_db.add(event)
        test_db.commit()
        
        # Process chunk
        memory_service._process_session_chunk(
            test_db,
            session_id=session_id,
            agent_id=agent_id,
            cursor=cursor,
            event_end_id=event.id,
        )
        test_db.commit()
        
        # Verify chunk was created with fallback values
        chunks = test_db.query(SessionChunk).all()
        assert len(chunks) == 1
        
        chunk = chunks[0]
        assert chunk.chunk_type == "discussion"  # Fallback type
        assert chunk.confidence == 0.5  # Fallback confidence
        assert chunk.topic_tags == []  # Fallback empty tags


class TestSessionChunkRetrieval:
    """Test session chunk retrieval functionality."""

    @patch('omnimind_backend.infra.config.get_settings')
    def test_retrieval_fallback_to_chunks(self, mock_settings, test_db, memory_service):
        """Test that retrieval falls back to chunks when no embeddings are found."""
        # Mock settings to enable session chunks
        mock_settings.return_value = Mock(
            enable_session_chunks=True,
            memory_retrieval_top_k=3,
        )
        
        session_id = "test_session"
        agent_id = "test_agent"
        
        # Create some chunks
        for i in range(3):
            chunk = SessionChunk(
                session_id=session_id,
                agent_id=agent_id,
                sequence=i + 1,
                chunk_type="discussion",
                content_summary=f"Discussion about topic {i}",
                topic_tags=[f"topic{i}"],
                token_count=1000,
                event_start_id=i * 10 + 1,
                event_end_id=i * 10 + 10,
                confidence=0.8,
            )
            test_db.add(chunk)
        
        test_db.commit()
        
        # Test retrieval (should fall back to chunks since no embeddings exist)
        result = memory_service.retrieve_context(
            test_db,
            session_id=session_id,
            agent_id=agent_id,
            query="test query",
        )
        
        assert result.context is not None
        assert "Discussion about topic" in result.context
        assert len(result.references) == 3
        assert all(ref.startswith("chunk:") for ref in result.references)

    @patch('omnimind_backend.infra.config.get_settings')
    def test_retrieval_prefers_embeddings_over_chunks(self, mock_settings, test_db, memory_service):
        """Test that retrieval prefers embeddings over chunks."""
        # Mock settings
        mock_settings.return_value = Mock(
            enable_session_chunks=True,
            memory_retrieval_top_k=3,
        )
        
        session_id = "test_session"
        agent_id = "test_agent"
        
        # Create chunks
        chunk = SessionChunk(
            session_id=session_id,
            agent_id=agent_id,
            sequence=1,
            chunk_type="discussion",
            content_summary="Chunk content",
            topic_tags=["topic"],
            token_count=1000,
            event_start_id=1,
            event_end_id=10,
            confidence=0.8,
        )
        test_db.add(chunk)
        
        # Create embedding (should be preferred over chunks)
        embedding = AgentMemoryEmbedding(
            session_id=session_id,
            agent_id=agent_id,
            source_type="message",
            source_id="123",
            content_excerpt="Embedding content",
            vector=[0.1] * 256,  # Mock vector
        )
        test_db.add(embedding)
        test_db.commit()
        
        # Test retrieval (should use embedding, not chunk)
        result = memory_service.retrieve_context(
            test_db,
            session_id=session_id,
            agent_id=agent_id,
            query="test query",
        )
        
        assert result.context is not None
        assert "Embedding content" in result.context
        assert len(result.references) == 1
        assert "message:123" in result.references

    @patch('omnimind_backend.infra.config.get_settings')
    def test_retrieval_disabled_when_chunks_flag_false(self, mock_settings, test_db, memory_service):
        """Test that chunk retrieval is disabled when enable_session_chunks=False."""
        # Mock settings to disable session chunks
        mock_settings.return_value = Mock(
            enable_session_chunks=False,
            memory_retrieval_top_k=3,
        )
        
        session_id = "test_session"
        agent_id = "test_agent"
        
        # Create chunks (should be ignored)
        chunk = SessionChunk(
            session_id=session_id,
            agent_id=agent_id,
            sequence=1,
            chunk_type="discussion",
            content_summary="Chunk content",
            topic_tags=["topic"],
            token_count=1000,
            event_start_id=1,
            event_end_id=10,
            confidence=0.8,
        )
        test_db.add(chunk)
        test_db.commit()
        
        # Test retrieval (should not use chunks)
        result = memory_service.retrieve_context(
            test_db,
            session_id=session_id,
            agent_id=agent_id,
            query="test query",
        )
        
        # Should return empty context since no embeddings exist and chunks are disabled
        assert result.context == ""
        assert len(result.references) == 0
