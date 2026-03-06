"""Data persistence exceptions.

All exceptions related to database operations, vector stores, caching, and migrations.
"""

from .database import DatabaseError, ConnectionError, MigrationError
from .vector import VectorStoreError
from .cache import CacheError

__all__ = [
    "DatabaseError",
    "ConnectionError",
    "MigrationError",
    "VectorStoreError",
    "CacheError",
]
