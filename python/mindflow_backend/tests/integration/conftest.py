"""Fixtures para testes de integração do Intelligent Memory System.

Fornece banco de dados real (SQLite em memória) para testes de integração.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

# Configurar banco de teste antes de importar os modelos
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from mindflow_backend.memory.storage.models import Base


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for tests using SQLite in memory.

    Creates all tables before each test and drops them after.
    """
    # Create async engine for SQLite in memory
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Provide session
    async with async_session_factory() as session:
        yield session

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def initialized_category_manager(db_session: AsyncSession) -> Any:
    """Provide an initialized CategoryManager with database."""
    from mindflow_backend.memory.category_manager import CategoryManager

    manager = CategoryManager()
    await manager.initialize(db_session)
    return manager


@pytest_asyncio.fixture
async def initialized_memory_service(db_session: AsyncSession) -> Any:
    """Provide an initialized MemoryService with database."""
    from mindflow_backend.memory.memory_service import MemoryService
    from mindflow_backend.memory.category_manager import CategoryManager

    # Create service with mocked embedding (we don't want to call real LLM in tests)
    from unittest.mock import AsyncMock, patch

    service = MemoryService()
    service.category_manager = CategoryManager()
    service.embedding_service = AsyncMock()
    service.embedding_service.generate_embedding.return_value = [0.1] * 1536
    service.embedding_service.generate_batch_embeddings.return_value = [[0.1] * 1536]

    # Patch the get_db_session to return our test session
    with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

        await service.initialize()
        yield service


@pytest.fixture
def sample_memory_data() -> dict[str, Any]:
    """Provide sample memory data for tests."""
    return {
        "content": "User prefers async/await patterns in Python",
        "memory_type": "preference",
        "scope": "global",
        "category": "user_preferences",
        "subcategory": "python_style",
        "importance": 0.8,
        "tags": ["python", "async", "coding_style"],
        "source_agent_id": "agent_001",
        "file_path": "/home/user/project/main.py",
    }
