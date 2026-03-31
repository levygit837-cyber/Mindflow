"""Core storage abstractions and base classes.

Provides unified interfaces that integrate with the global interfaces system
and schemas defined in the MindFlow backend.
"""

from .exceptions import (
    CacheError,
    ConnectionError,
    DatabaseError,
    MigrationError,
    StorageError,
    VectorError,
)
from .interfaces import (
    CacheInterface,
    ConnectionPoolInterface,
    DatabaseInterface,
    MigrationInterface,
    RepositoryInterface,
    StorageInterface,
    VectorDatabaseInterface,
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
