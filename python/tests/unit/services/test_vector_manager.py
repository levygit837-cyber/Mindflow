"""Tests for VectorManager and vector database implementations.

This module tests the vector database abstraction layer including:
- PgVectorDatabase implementation
- VectorManager operations
- Vector similarity search
- CRUD operations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.services.vector_manager import (
    PgVectorDatabase,
    VectorManager,
    get_vector_manager,
)


class TestPgVectorDatabase:
    """Test PgVectorDatabase implementation."""

    @pytest.fixture
    def pg_db(self):
        """Create a PgVectorDatabase instance."""
        return PgVectorDatabase(
            connection_string="postgresql://test:test@localhost/test",
            dimensions=256
        )

    def test_initialization(self, pg_db):
        """Test PgVectorDatabase initialization."""
        assert pg_db.connection_string == "postgresql://test:test@localhost/test"
        assert pg_db.dimensions == 256
        assert not pg_db._initialized

    def test_sanitize_table_name(self, pg_db):
        """Test table name sanitization."""
        # Valid names
        assert pg_db._sanitize_table_name("test_collection") == "test_collection"
        assert pg_db._sanitize_table_name("test-collection") == "test-collection"
        assert pg_db._sanitize_table_name("test123") == "test123"
        
        # Names with invalid characters
        assert pg_db._sanitize_table_name("test.collection") == "test_collection"
        assert pg_db._sanitize_table_name("test;collection") == "test_collection"
        
        # Names starting with non-letter
        assert pg_db._sanitize_table_name("123test") == "vec_123test"

    def test_vector_to_pgvector_str(self, pg_db):
        """Test vector to pgvector string conversion."""
        assert pg_db._vector_to_pgvector_str([1.0, 2.0, 3.0]) == "[1.0,2.0,3.0]"
        assert pg_db._vector_to_pgvector_str([]) == "[]"
        assert pg_db._vector_to_pgvector_str([0.1]) == "[0.1]"

    def test_pgvector_str_to_list(self, pg_db):
        """Test pgvector string to list conversion."""
        assert pg_db._pgvector_str_to_list("[1.0,2.0,3.0]") == [1.0, 2.0, 3.0]
        assert pg_db._pgvector_str_to_list("[]") == []
        assert pg_db._pgvector_str_to_list("") == []

    @pytest.mark.asyncio
    async def test_initialize(self, pg_db):
        """Test database initialization."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        
        with patch('mindflow_backend.services.vector_manager.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            await pg_db.initialize()
        
        assert pg_db._initialized
        mock_session.execute.assert_called_once()


class TestVectorManager:
    """Test VectorManager functionality."""

    @pytest.fixture
    def vector_manager(self):
        """Create a VectorManager instance."""
        return VectorManager()

    def test_initialization(self, vector_manager):
        """Test VectorManager initialization."""
        assert vector_manager._db is None
        assert vector_manager._provider is None

    @pytest.mark.asyncio
    async def test_create_session_collection(self, vector_manager):
        """Test creating a session collection."""
        mock_db = AsyncMock()
        mock_db.dimensions = 256
        vector_manager._db = mock_db
        vector_manager._provider = "pgvector"
        
        await vector_manager.create_session_collection("test-session")
        
        mock_db.create_collection.assert_called_once_with("session_test-session", 256)

    @pytest.mark.asyncio
    async def test_store_session_embeddings(self, vector_manager):
        """Test storing session embeddings."""
        mock_db = AsyncMock()
        mock_db.insert_vectors.return_value = ["vec-1", "vec-2"]
        vector_manager._db = mock_db
        
        embeddings = [
            {"id": "1", "vector": [0.1, 0.2], "metadata": {"text": "test"}},
            {"id": "2", "vector": [0.3, 0.4], "metadata": {"text": "test2"}},
        ]
        
        result = await vector_manager.store_session_embeddings("test-session", embeddings)
        
        assert result == ["vec-1", "vec-2"]
        mock_db.insert_vectors.assert_called_once_with("session_test-session", embeddings)

    @pytest.mark.asyncio
    async def test_search_session_context(self, vector_manager):
        """Test searching session context."""
        mock_db = AsyncMock()
        mock_db.search_vectors.return_value = [
            {"id": "vec-1", "score": 0.95, "metadata": {"text": "test"}}
        ]
        vector_manager._db = mock_db
        
        query_vector = [0.1, 0.2, 0.3]
        results = await vector_manager.search_session_context(
            "test-session",
            query_vector,
            limit=5,
            score_threshold=0.8
        )
        
        assert len(results) == 1
        assert results[0]["score"] == 0.95
        mock_db.search_vectors.assert_called_once_with(
            "session_test-session",
            query_vector,
            5,
            0.8
        )


class TestVectorUtilities:
    """Test vector utility functions."""

    def test_pgvector_table_name_sanitization_edge_cases(self):
        """Test edge cases in table name sanitization."""
        db = PgVectorDatabase("test", 256)
        
        # Very long names
        long_name = "a" * 100
        sanitized = db._sanitize_table_name(long_name)
        assert len(sanitized) <= 63
        
        # Empty name
        assert db._sanitize_table_name("") == "vec_"
        
        # SQL injection attempts
        assert ";" not in db._sanitize_table_name("test; DROP TABLE")
        assert "'" not in db._sanitize_table_name("test' OR '1'='1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
