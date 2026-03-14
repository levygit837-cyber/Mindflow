"""Core storage abstractions and base classes.

Provides unified interfaces that integrate with the global interfaces system
and schemas defined in the MindFlow backend.
"""

from .interfaces import (
    StorageInterface,
    DatabaseInterface,
    VectorDatabaseInterface,
    CacheInterface,
    RepositoryInterface,
    ConnectionPoolInterface,
    MigrationInterface,
)

from .exceptions import (
    StorageError,
    DatabaseError,
    VectorError,
    CacheError,
    ConnectionError,
    MigrationError,
)

__all__ = [
    # Interfaces
    "StorageInterface",
    "DatabaseInterface", 
    "VectorDatabaseInterface",
    "CacheInterface",
    "RepositoryInterface",
    "ConnectionPoolInterface",
    "MigrationInterface",
    # Exceptions
    "StorageError",
    "DatabaseError",
    "VectorError", 
    "CacheError",
    "ConnectionError",
    "MigrationError",
]
