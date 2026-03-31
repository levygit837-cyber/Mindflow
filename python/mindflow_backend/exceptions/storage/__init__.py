"""Data persistence exceptions.

All exceptions related to database operations, vector stores, caching, and migrations.
"""

from .cache import CacheError
from .database import ConnectionError, DatabaseError, MigrationError
from .vector import VectorStoreError

__all__ = [
    "DatabaseError",
    "ConnectionError",
    "MigrationError",
    "VectorStoreError",
    "CacheError",
]
