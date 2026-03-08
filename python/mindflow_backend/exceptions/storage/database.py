"""Database operation exceptions.

Exceptions for database connections, queries, transactions,
and migration failures.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_simple import InfrastructureError


class DatabaseError(InfrastructureError):
    """Database operation failure."""
    
    def __init__(
        self,
        message: str,
        *,
        database_name: str | None = None,
        operation: str | None = None,
        query: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            service="database",
            component="storage",
            context={"operation": operation} if operation else None,
            **kwargs
        )
        self.database_name = database_name
        self.query = query


class ConnectionError(DatabaseError):
    """Database connection failure."""
    
    def __init__(
        self,
        message: str,
        *,
        connection_string: str | None = None,
        pool_exhausted: bool = False,
        **kwargs,
    ):
        super().__init__(
            message,
            context={"operation": "connect"},
            **kwargs
        )
        self.connection_string = connection_string
        self.pool_exhausted = pool_exhausted


class MigrationError(DatabaseError):
    """Database migration failure."""
    
    def __init__(
        self,
        message: str,
        *,
        migration_version: str | None = None,
        target_version: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            context={"operation": "migrate"},
            **kwargs
        )
        self.migration_version = migration_version
        self.target_version = target_version
