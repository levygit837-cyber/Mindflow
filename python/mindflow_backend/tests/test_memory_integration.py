"""Test memory integration functionality.

Tests context storage, retrieval, and token range functionality
for the new simple memory service.
"""

import asyncio
import os
import tempfile

import pytest

from mindflow_backend.orchestrator.memory_integration import (
    MemoryIntegration,
    get_token_range_context,
)
from mindflow_backend.services.memory import create_memory_service
from mindflow_backend.services.nlp_embeddings import EmbeddingMethod


class TestMemoryService:
    """Test the simple memory service."""
    
    @pytest.fixture
    async def memory_service(self):
        """Create a temporary memory service for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_memory.db")
            service = create_memory_service(
                db_path=db_path,
                embedding_method=EmbeddingMethod.TFIDF,
                max_context_length=10000,
            )
            await service.initialize()
            yield service
    
    @pytest.mark.asyncio
    async def test_store_context(self, memory_service):
        """Test storing context entries."""
        context_id = await memory_service.store_context(
            session_id="test_session",
            agent_id="test_agent",
            content="This is a test message",
            token_start=0,
            token_end=5,
        )
        
        assert context_id is not None
        assert len(context_id) > 0
    
    @pytest.mark.asyncio
    async def test_retrieve_context_by_range(self, memory_service):
        """Test retrieving context by token range."""
        # Store multiple entries
        await memory_service.store_context(
            session_id="test_session",
            agent_id="user",
            content="First message",
            token_start=0,
            token_end=3,
        )
        
        await memory_service.store_context(
            session_id="test_session",
            agent_id="agent",
            content="Second message",
            token_start=3,
            token_end=6,
        )
        
        # Retrieve by range
        context = await memory_service.get_context(
            session_id="test_session",
            token_start=0,
            token_end=6,
        )
        
        assert len(context) == 2
        assert context[0].content == "First message"
        assert context[1].content == "Second message"
    
    @pytest.mark.asyncio
    async def test_search_context(self, memory_service):
        """Test semantic context search."""
        # Store entries
        await memory_service.store_context(
            session_id="test_session",
            agent_id="user",
            content="Python programming tutorial",
            token_start=0,
            token_end=4,
        )
        
        await memory_service.store_context(
            session_id="test_session",
            agent_id="agent",
            content="Machine learning algorithms",
            token_start=4,
            token_end=8,
        )
        
        # Search for programming-related content
        results = await memory_service.search_context(
            session_id="test_session",
            query="programming code",
            limit=5,
        )
        
        assert len(results) >= 1
        # Should find the Python programming entry
        found_programming = any("programming" in entry.content.lower() for entry, _ in results)
        assert found_programming
    
    @pytest.mark.asyncio
    async def test_session_stats(self, memory_service):
        """Test session statistics."""
        # Store some entries
        await memory_service.store_context(
            session_id="test_session",
            agent_id="user",
            content="Message 1",
            token_start=0,
            token_end=3,
        )
        
        await memory_service.store_context(
            session_id="test_session",
            agent_id="agent",
            content="Message 2",
            token_start=3,
            token_end=6,
        )
        
        # Get stats
        stats = await memory_service.get_session_stats("test_session")
        
        assert stats["entry_count"] == 2
        assert stats["min_token"] == 0
        assert stats["max_token"] == 6
        assert stats["total_tokens"] == 6


class TestMemoryIntegration:
    """Test memory integration functionality."""
    
    @pytest.fixture
    async def memory_integration(self):
        """Create a temporary memory integration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_integration.db")
            integration = MemoryIntegration(
                db_path=db_path,
                embedding_method=EmbeddingMethod.TFIDF,
                auto_store=True,
                auto_retrieve=True,
            )
            await integration.initialize()
            yield integration
    
    @pytest.mark.asyncio
    async def test_store_interaction(self, memory_integration):
        """Test storing interactions."""
        context_id = await memory_integration.store_interaction(
            session_id="test_session",
            agent_id="test_agent",
            content="Test interaction",
            token_start=0,
            token_end=5,
        )
        
        assert context_id is not None
        assert len(context_id) > 0
    
    @pytest.mark.asyncio
    async def test_retrieve_context(self, memory_integration):
        """Test retrieving context."""
        # Store some interactions
        await memory_integration.store_interaction(
            session_id="test_session",
            agent_id="user",
            content="What is Python?",
            token_start=0,
            token_end=4,
        )
        
        await memory_integration.store_interaction(
            session_id="test_session",
            agent_id="agent",
            content="Python is a programming language",
            token_start=4,
            token_end=9,
        )
        
        # Retrieve by query
        context = await memory_integration.retrieve_context(
            session_id="test_session",
            query="programming",
            limit=5,
        )
        
        assert len(context) >= 1
        assert any("programming" in entry["content"].lower() for entry in context)
    
    @pytest.mark.asyncio
    async def test_token_range_context(self, memory_integration):
        """Test token range context retrieval."""
        # Store interactions with specific token ranges
        await memory_integration.store_interaction(
            session_id="test_session",
            agent_id="user",
            content="Early conversation",
            token_start=0,
            token_end=3,
        )
        
        await memory_integration.store_interaction(
            session_id="test_session",
            agent_id="agent",
            content="Middle conversation",
            token_start=10,
            token_end=13,
        )
        
        await memory_integration.store_interaction(
            session_id="test_session",
            agent_id="user",
            content="Late conversation",
            token_start=20,
            token_end=23,
        )
        
        # Test helper function
        context = await get_token_range_context(
            session_id="test_session",
            start_token=0,
            end_token=5,
        )
        
        # Should only include early conversation
        assert "Early conversation" in context
        assert "Middle conversation" not in context
        assert "Late conversation" not in context


class TestEmbeddingMethods:
    """Test different embedding methods."""
    
    @pytest.mark.asyncio
    async def test_tfidf_embeddings(self):
        """Test TF-IDF embedding generation."""
        from mindflow_backend.services.nlp_embeddings import create_embedding_service
        
        try:
            service = create_embedding_service(method=EmbeddingMethod.TFIDF)
            
            # Fit with sample texts
            sample_texts = [
                "Python programming tutorial",
                "Machine learning basics",
                "Web development guide",
            ]
            await service.fit(sample_texts)
            
            # Generate embeddings
            embeddings = await service.generate_embeddings("test query")
            
            assert len(embeddings) == 1
            assert len(embeddings[0]) > 0
            assert service.get_dimension() > 0
        except ImportError:
            # Skip test if scikit-learn is not available
            pytest.skip("scikit-learn not available for TF-IDF test")
    
    @pytest.mark.asyncio
    async def test_hybrid_embeddings(self):
        """Test hybrid embedding generation."""
        from mindflow_backend.services.nlp_embeddings import create_hybrid_service
        
        try:
            service = create_hybrid_service(
                primary_method=EmbeddingMethod.TFIDF,
                secondary_method=EmbeddingMethod.TFIDF,  # Use same method for testing
            )
            
            # Fit with sample texts
            sample_texts = [
                "First document",
                "Second document",
                "Third document",
            ]
            await service.fit(sample_texts)
            
            # Generate embeddings
            embeddings = await service.generate_embeddings("test query", use_hybrid=True)
            
            assert len(embeddings) == 1
            assert len(embeddings[0]) > 0
        except ImportError:
            # Skip test if scikit-learn is not available
            pytest.skip("scikit-learn not available for hybrid test")


class TestTokenRangeRetrieval:
    """Test specific token range retrieval scenarios."""
    
    @pytest.fixture
    async def populated_memory_service(self):
        """Create a memory service with test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_range.db")
            try:
                service = create_memory_service(
                    db_path=db_path,
                    embedding_method=EmbeddingMethod.TFIDF,
                )
                await service.initialize()
            except ImportError:
                pytest.skip("scikit-learn not available for token range test")
                return
            
            # Create test data simulating 800K tokens
            session_id = "large_session"
            
            # Store entries across different token ranges
            test_entries = [
                ("Early discussion about AI", 0, 100),
                ("Machine learning concepts", 100, 200),
                ("Deep learning details", 200, 300),
                ("Neural network architecture", 300, 400),
                ("Training algorithms", 400, 500),
                ("Optimization techniques", 500, 600),
                ("Recent developments", 600, 700),
                ("Future directions", 700, 800),
                # Simulate more entries up to 800K
                ("Mid-range conversation", 400000, 400100),
                ("Recent interaction", 799900, 800000),
            ]
            
            for content, start, end in test_entries:
                await service.store_context(
                    session_id=session_id,
                    agent_id="test_agent",
                    content=content,
                    token_start=start,
                    token_end=end,
                )
            
            yield service, session_id
    
    @pytest.mark.asyncio
    async def test_retrieve_early_context(self, populated_memory_service):
        """Test retrieving context from 0-10K token range."""
        service, session_id = populated_memory_service
        
        # Retrieve early context (0-10K)
        context = await service.get_context(
            session_id=session_id,
            token_start=0,
            token_end=10000,
        )
        
        assert len(context) >= 8  # Should include early entries
        assert any("Early discussion" in entry.content for entry in context)
        assert any("Future directions" in entry.content for entry in context)
    
    @pytest.mark.asyncio
    async def test_retrieve_recent_context(self, populated_memory_service):
        """Test retrieving recent context near 800K."""
        service, session_id = populated_memory_service
        
        # Retrieve recent context (790K-800K)
        context = await service.get_context(
            session_id=session_id,
            token_start=790000,
            token_end=800000,
        )
        
        assert len(context) >= 1
        assert any("Recent interaction" in entry.content for entry in context)
    
    @pytest.mark.asyncio
    async def test_search_in_token_range(self, populated_memory_service):
        """Test semantic search within specific token range."""
        service, session_id = populated_memory_service
        
        # Search for "learning" in early range (0-500)
        results = await service.search_context(
            session_id=session_id,
            query="learning",
            token_range=(0, 500),
            limit=5,
        )
        
        assert len(results) >= 2
        # Should find machine learning and deep learning entries
        learning_entries = [entry for entry, _ in results if "learning" in entry.content.lower()]
        assert len(learning_entries) >= 2


if __name__ == "__main__":
    # Run basic tests
    async def run_basic_tests():
        """Run basic functionality tests."""
        print("Running basic memory integration tests...")
        
        try:
            # Test memory service
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = os.path.join(temp_dir, "basic_test.db")
                service = create_memory_service(
                    db_path=db_path,
                    embedding_method=EmbeddingMethod.TFIDF,
                )
                await service.initialize()
                
                # Store and retrieve
                context_id = await service.store_context(
                    session_id="basic_test",
                    agent_id="test_agent",
                    content="Basic test message",
                    token_start=0,
                    token_end=4,
                )
                
                context = await service.get_context("basic_test")
                assert len(context) == 1
                assert context[0].content == "Basic test message"
                
                print("✅ Basic memory service test passed")
                
                # Test token range retrieval
                await service.store_context(
                    session_id="range_test",
                    agent_id="user",
                    content="Early message",
                    token_start=0,
                    token_end=3,
                )
                
                await service.store_context(
                    session_id="range_test",
                    agent_id="agent",
                    content="Later message",
                    token_start=10,
                    token_end=13,
                )
                
                early_context = await service.get_context("range_test", 0, 5)
                assert len(early_context) == 1
                assert early_context[0].content == "Early message"
                
                print("✅ Token range test passed")
                
                # Test search
                await service.store_context(
                    session_id="search_test",
                    agent_id="user",
                    content="Python programming guide",
                    token_start=0,
                    token_end=4,
                )
                
                results = await service.search_context("search_test", "programming")
                assert len(results) >= 1
                
                print("✅ Search test passed")
        
        except ImportError as e:
            print(f"⚠️  Skipped tests due to missing dependency: {e}")
        
        print("All basic tests completed!")
    
    # Run the tests
    asyncio.run(run_basic_tests())
