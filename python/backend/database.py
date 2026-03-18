from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Database URL for SQLite with aiosqlite
# Four slashes denote an absolute path
DATABASE_URL = "sqlite+aiosqlite:////tmp/agenda-app/backend/agenda.db"

# Create the async engine
# SQLite requires some extra parameters for async/thread safety in some environments,
# but for basic async SQLite usage, this is standard.
engine = create_async_engine(DATABASE_URL, echo=True)

# Create async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declarative base class for models
class Base(DeclarativeBase):
    pass

async def create_all() -> None:
    """Creates all tables defined in the Base metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
