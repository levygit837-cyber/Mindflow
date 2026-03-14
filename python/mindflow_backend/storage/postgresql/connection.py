"""Legacy database connection wrapper.

DEPRECATED: This module is deprecated and will be removed in v2.0.
Use mindflow_backend.infra.database.connection.get_db_session() instead.

For backward compatibility, this module will redirect to the new system.
"""

import warnings
from contextlib import contextmanager, asynccontextmanager
from typing import Any, Generator, AsyncGenerator
from sqlalchemy.orm import Session

from mindflow_backend.infra.database.connection import get_db_session

# Legacy setup for backward compatibility
@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Legacy database session context manager.
    
    DEPRECATED: This function is deprecated and will be removed in v2.0. 
    Use mindflow_backend.infra.database.get_db_session() instead.
    This wrapper maintains backward compatibility during migration.
    """
    warnings.warn(
        "db_session() is deprecated and will be removed in v2.0. "
        "Use mindflow_backend.infra.database.get_db_session() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from mindflow_backend.infra.database.connection import get_db_session
    with get_db_session() as session:
        yield session

@asynccontextmanager
async def async_db_session() -> AsyncGenerator[Session, None]:
    """Legacy async database session context manager.
    
    DEPRECATED: This function is deprecated and will be removed in v2.0. 
    Use mindflow_backend.infra.database.connection.get_async_db_session() instead.
    This wrapper maintains backward compatibility during migration.
    """
    warnings.warn(
        "async_db_session() is deprecated and will be removed in v2.0. "
        "Use mindflow_backend.infra.database.connection.get_async_db_session() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from mindflow_backend.infra.database.connection import get_async_db_session
    async with get_async_db_session() as session:
        yield session
