"""Abstract base class for cache backends.

Defines the interface that all cache backends must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import CacheEntry


class CacheBackend(ABC):
    """Abstract base class for cache backends.

    All cache backends (memory, Redis, etc.) must implement this interface.
    """

    @abstractmethod
    async def get(self, key: str) -> CacheEntry | None:
        """Get cache entry by key.

        Args:
            key: Cache key

        Returns:
            Cache entry or None if not found
        """
        pass

    @abstractmethod
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry.

        Args:
            key: Cache key
            entry: Cache entry to store

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries.

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern.

        Args:
            pattern: Glob pattern for key matching

        Returns:
            List of matching keys
        """
        pass

    @abstractmethod
    async def size(self) -> int:
        """Get number of entries in cache.

        Returns:
            Number of entries
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get cache backend statistics.

        Returns:
            Dictionary with statistics
        """
        pass