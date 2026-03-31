"""Test suite for Semantic Context System.

Validates the integration of multilingual embeddings, semantic search,
and context-aware orchestration components.
"""

import asyncio
from uuid import uuid4

import pytest

from mindflow_backend.orchestrator.decomposition.context_aware_resolver import (
    ContextAwareResolver,
)
from mindflow_backend.orchestrator.semantic_context_manager import (
    SemanticContextManager,
)
from mindflow_backend.services.multilingual_embeddings import MultilingualEmbeddingService


class TestMultilingualEmbeddings:
    """Test multilingual embedding service."""
    
    @pytest.fixture
    async def embedding_service(self):
        service = MultilingualEmbeddingService()
        await service.initialize()
        return service
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self, embedding_service):
        """Test basic embedding generation."""
        text = "Fix authentication bug in login system"
        embedding = await embedding_service.generate_embedding(text)
        
        assert len(embedding) > 0
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)
        assert len(embedding) == embedding_service.get_embedding_dimension()
    
    @pytest.mark.asyncio
    async def test_batch_embeddings(self, embedding_service):
        """Test batch embedding generation."""
        texts = [
            "Fix authentication bug",
            "Corrigir bug de autenticação",
            "Arreglar bug de autenticación",
        ]
        
        embeddings = await embedding_service.generate_batch_embeddings(texts)
        
        assert len(embeddings) == len(texts)
        for embedding in embeddings:
            assert len(embedding) == embedding_service.get_embedding_dimension()
    
    @pytest.mark.asyncio
    async def test_language_detection(self, embedding_service):
        """Test language detection."""
        tests = [
            ("Fix authentication bug", "en"),
            ("Corrigir bug de autenticação", "pt"),
            ("Arreglar bug de autenticación", "es"),
        ]
        
        for text, expected_lang in tests:
            detected = await embedding_service.detect_language(text)
            assert detected == expected_lang
    
    @pytest.mark.asyncio
    async def test_similarity_calculation(self, embedding_service):
        """Test similarity calculation between embeddings."""
        text1 = "Fix authentication bug"
        text2 = "Corrigir bug de autenticação"  # Similar meaning
        text3 = "Add new user interface"  # Different meaning
        
        emb1 = await embedding_service.generate_embedding(text1)
        emb2 = await embedding_service.generate_embedding(text2)
        emb3 = await embedding_service.generate_embedding(text3)
        
        sim_12 = await embedding_service.calculate_similarity(emb1, emb2)
        sim_13 = await embedding_service.calculate_similarity(emb1, emb3)
        
        # Similar texts should have higher similarity
        assert sim_12 > sim_13
        assert 0.0 <= sim_12 <= 1.0
        assert 0.0 <= sim_13 <= 1.0


class TestSemanticContextManager:
    """Test semantic context manager."""
    
    @pytest.fixture
    async def context_manager(self):
        from mindflow_backend.agents.context.vector_store import InMemoryVectorStore
        vector_store = InMemoryVectorStore()
        manager = SemanticContextManager(vector_store)
        await manager.initialize()
        return manager
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_context(self, context_manager):
        """Test storing and retrieving context."""
        session_id = str(uuid4())
        task_id = str(uuid4())
        
        # Store context
        vector_id = await context_manager.store_task_context(
            task_id=task_id,
            agent_type="analyst",
            content="Codebase uses FastAPI with PostgreSQL",
            metadata={"session_id": session_id},
        )
        
        assert vector_id is not None
        
        # Retrieve context
        matches = await context_manager.find_relevant_context(
            task_id="new_task",
            query="FastAPI database setup",
            session_id=session_id,
            limit=5,
        )
        
        assert len(matches) > 0
        assert matches[0].agent_type == "analyst"
        assert matches[0].task_id == task_id
        assert "FastAPI" in matches[0].content
    
    @pytest.mark.asyncio
    async def test_dependency_resolution(self, context_manager):
        """Test dependency resolution and waiting."""
        session_id = str(uuid4())
        task1_id = str(uuid4())
        task2_id = str(uuid4())
        
        # Store first task context
        await context_manager.store_task_context(
            task_id=task1_id,
            agent_type="analyst",
            content="Codebase analysis completed",
            metadata={"session_id": session_id},
        )
        
        # Mark as completed
        await context_manager.update_task_status(
            task_id=task1_id,
            status="completed",
            session_id=session_id,
        )
        
        # Wait for dependency (should be ready)
        wait_result = await context_manager.wait_for_context(
            task_id=task2_id,
            required_context_ids=[task1_id],
            session_id=session_id,
            timeout=5,
        )
        
        assert wait_result["status"] == "ready"
        assert len(wait_result["contexts"]) == 1
        assert wait_result["contexts"][0]["task_id"] == task1_id
    
    @pytest.mark.asyncio
    async def test_context_caching(self, context_manager):
        """Test context caching functionality."""
        session_id = str(uuid4())
        task_id = str(uuid4())
        
        # Store context
        await context_manager.store_task_context(
            task_id=task_id,
            agent_type="coder",
            content="Fixed authentication bug",
            metadata={"session_id": session_id},
        )
        
        # Check cache
        cached = await context_manager.get_cached_context(task_id)
        assert cached is not None
        assert cached.task_id == task_id
        assert cached.agent_type == "coder"
        
        # Clear cache
        await context_manager.clear_cache(task_id)
        cached_after = await context_manager.get_cached_context(task_id)
        assert cached_after is None


class TestContextAwareResolver:
    """Test context-aware resolver."""
    
    @pytest.fixture
    async def resolver(self):
        resolver = ContextAwareResolver()
        await resolver._ensure_initialized()
        return resolver
    
    @pytest.mark.asyncio
    async def test_context_resolution(self, resolver):
        """Test resolution with context awareness."""
        from uuid import UUID

        from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
            ComponentOwner,
            SubTaskContract,
        )
        
        session_id = str(uuid4())
        
        # Create test contract
        contract = SubTaskContract(
            task_id=UUID(),
            parent_id=UUID(),
            title="Fix Bug",
            scope="Fix authentication bug in login",
            dependencies=[],
            context_boundary="Authentication module",
            expected_artifacts=["Fixed code"],
            owner_agent=ComponentOwner.CODER,
            priority="high",
        )
        
        # Mock some prior results
        prior_results = {
            "analyst_task": "The codebase uses JWT for authentication",
        }
        
        # Resolve (this will use semantic search)
        result = await resolver.resolve(
            contract=contract,
            prior_results=prior_results,
            provider="vertexai",
            model="gemini-3-flash-preview",
            memory_context="User reported login issues",
            session_id=session_id,
        )
        
        assert "task_id" in result
        assert "title" in result
        assert "result" in result
        assert "context_used" in result
        assert isinstance(result["result"], str)
        assert len(result["result"]) > 0


class TestIntegration:
    """Integration tests for the complete semantic context system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow from decomposition to resolution."""
        from mindflow_backend.orchestrator.decomposition.tasker_v2 import TaskerV2
        
        # Initialize components
        tasker = TaskerV2()
        await tasker._ensure_initialized()
        
        session_id = str(uuid4())
        
        # Mock a complex request
        message = """
        Analyze the authentication system and fix the login bug.
        The issue occurs when users try to login with expired tokens.
        After fixing, add comprehensive tests.
        """
        
        # Decompose the task
        main, components = await tasker.decompose(
            message=message,
            session_id=session_id,
            complexity_score=0.8,
            provider="vertexai",
            model="gemini-3-flash-preview",
        )
        
        # Verify decomposition
        assert main.goal is not None
        assert len(components) >= 2  # Should have at least analysis and fix tasks
        
        # Check that components have proper metadata
        for comp in components:
            assert comp.metadata is not None
            assert "session_id" in comp.metadata
            assert "complexity_score" in comp.metadata


# Performance benchmarks
class TestPerformance:
    """Performance tests for semantic context system."""
    
    @pytest.mark.asyncio
    async def test_embedding_generation_performance(self):
        """Benchmark embedding generation performance."""
        import time
        
        service = MultilingualEmbeddingService()
        await service.initialize()
        
        texts = [f"Test text {i}" for i in range(100)]
        
        start_time = time.time()
        embeddings = await service.generate_batch_embeddings(texts)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = len(texts) / duration
        
        assert len(embeddings) == len(texts)
        assert throughput > 10  # Should process at least 10 texts/second
        
        print(f"Embedding generation: {throughput:.2f} texts/second")
    
    @pytest.mark.asyncio
    async def test_context_search_performance(self):
        """Benchmark context search performance."""
        import time
        
        from mindflow_backend.agents.context.vector_store import InMemoryVectorStore
        from mindflow_backend.orchestrator.semantic_context_manager import SemanticContextManager
        
        vector_store = InMemoryVectorStore()
        manager = SemanticContextManager(vector_store)
        await manager.initialize()
        
        # Store many contexts
        session_id = str(uuid4())
        for i in range(50):
            await manager.store_task_context(
                task_id=f"task_{i}",
                agent_type="coder",
                content=f"Task content {i} with authentication and login details",
                metadata={"session_id": session_id},
            )
        
        # Benchmark search
        start_time = time.time()
        matches = await manager.find_relevant_context(
            task_id="search_task",
            query="authentication login fix",
            session_id=session_id,
            limit=10,
        )
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 1.0  # Should complete within 1 second
        assert len(matches) > 0
        
        print(f"Context search: {duration:.3f} seconds for {len(matches)} matches")


if __name__ == "__main__":
    # Run a quick integration test
    async def quick_test():
        print("Running quick integration test...")
        
        # Test embedding service
        service = MultilingualEmbeddingService()
        await service.initialize()
        
        embedding = await service.generate_embedding("Test authentication fix")
        print(f"Generated embedding: {len(embedding)} dimensions")
        
        # Test similarity
        similarity = await service.calculate_similarity(embedding, embedding)
        print(f"Self-similarity: {similarity:.3f}")
        
        print("✅ Basic integration test passed!")
    
    asyncio.run(quick_test())
