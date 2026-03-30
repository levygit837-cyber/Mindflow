"""Database connection management with robust pooling.

Provides advanced connection pooling, health monitoring,
and connection lifecycle management for PostgreSQL.

This module re-exports all components from the decomposed connection package.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.infra.logging import get_logger

from .connection.models import ConnectionMetrics, ConnectionStatus, PoolState
from .connection.pool_monitor import ConnectionPoolMonitor
from .connection.database_manager import DatabaseManager

_logger = get_logger(__name__)


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance.

    Returns:
        DatabaseManager instance
    """
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager.

    Yields:
        AsyncSession: Database session
    """
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        yield session


async def initialize_database() -> None:
    """Initialize global database manager."""
    db_manager = get_db_manager()
    await db_manager.initialize()


async def shutdown_database() -> None:
    """Shutdown global database manager."""
    db_manager = get_db_manager()
    await db_manager.close()


__all__ = [
    "ConnectionMetrics",
    "ConnectionStatus",
    "PoolState",
    "ConnectionPoolMonitor",
    "DatabaseManager",
    "get_db_manager",
    "get_db_session",
    "initialize_database",
    "shutdown_database",
]