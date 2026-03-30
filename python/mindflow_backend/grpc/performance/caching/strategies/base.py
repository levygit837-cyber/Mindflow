"""Abstract base class for cache eviction strategies.

Defines the interface that all cache strategies must implement.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..config import CacheConfig
from ..entry import CacheEntry


class CacheStrategy(ABC):
    """Base class for cache eviction strategies.

    All cache strategies (LRU, TTL, SizeBased, LFU) must implement this interface.
    """

    def __init__(self, config: CacheConfig):
        """Initialize cache strategy.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._lock = threading.RLock()

    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache.

        Args:
            key: Cache key

        Returns:
            Cache entry or None if not found
        """
        pass

    @abstractmethod
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache.

        Args:
            key: Cache key
            entry: Cache entry to store

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def remove(self, key: str) -> bool:
        """Remove entry from cache.

        Args:
            key: Cache key

        Returns:
            True if removed
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from cache."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get number of entries in cache.

        Returns:
            Number of entries
        """
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Clean up expired entries.

        Returns:
            Number of entries removed
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with statistics
        """
        pass