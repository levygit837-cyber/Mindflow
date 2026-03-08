"""Legacy database connection wrapper.

This module provides backward compatibility while migrating
to the new database infrastructure in infra/database/.
"""

from contextlib import contextmanager
from typing import Generator
import warnings

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.database.connection import get_db_manager

# Legacy setup for backward compatibility
settings = get_settings()
engine = create_engine(settings.database.url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Legacy database session context manager.
    
    DEPRECATED: Use mindflow_backend.infra.database.get_db_session() instead.
    This wrapper maintains backward compatibility during migration.
    """
    warnings.warn(
        "db_session() is deprecated. Use mindflow_backend.infra.database.get_db_session() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def async_db_session():
    """Async database session context manager using new infrastructure.
    
    Returns:
        AsyncSession: Database session with new infrastructure.
    """
    from mindflow_backend.infra.database.connection import get_db_session
    
    async with get_db_session() as session:
        yield session
