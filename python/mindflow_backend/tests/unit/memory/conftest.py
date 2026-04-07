"""Fixtures para testes unitários do Intelligent Memory System.

Fornece banco de dados real (SQLite em memória) para testes.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
