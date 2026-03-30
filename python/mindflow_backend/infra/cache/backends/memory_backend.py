"""L1 Memory cache backend with LRU eviction.

Provides in-memory caching with configurable eviction policies.
"""

from __future__ import annotations

import fnmatch
import threading
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from ..models import CacheEntry, CachePolicy
from .base import CacheBackend


class MemoryCacheBackend(CacheBackend):
    """L1 Memory cache backend with LRU eviction.

    Provides fast in-memory caching with support for multiple
    eviction policies (LRU, LFU, FIFO).

    Attributes:
        max_size: Maximum number of entries
        policy: Eviction policy to use
    """

    def __init__(self, max_size: int = 1000, policy: CachePolicy = CachePolicy.LRU):
        """Initialize memory cache backend.

        Args:
            max_size: Maximum number of entries
            policy: Eviction policy
        """
        self.max_size = max_size
        self.policy = policy
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
        }

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry from memory.

        Args:
            key: Cache key

        Returns:
            Cache entry or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            # Check expiration
            if entry.is_expired:
                del self._cache[key]
                self._stats["misses"] += 1
                return None

            # Update access for LRU
            if self.policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            entry.touch()
            self._stats["hits"] += 1
            return entry

    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry in memory.

        Args:
            key: Cache key
            entry: Cache entry to store

        Returns:
            True if successful
        """
        with self._lock:
            # Check if we need to evict
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict()

            self._cache[key] = entry
            self._stats["sets"] += 1

            # Move to end for LRU
            if self.policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            return True

    async def delete(self, key: str) -> bool:
        """Delete cache entry from memory.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cache entries.

        Returns:
            True if successful
        """
        with self._lock:
            self._cache.clear()
            return True

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern.

        Args:
            pattern: Glob pattern for key matching

        Returns:
            List of matching keys
        """
        with self._lock:
            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

    async def size(self) -> int:
        """Get number of entries in cache.

        Returns:
            Number of entries
        """
        with self._lock:
            return len(self._cache)

    def _evict(self) -> None:
        """Evict entries based on policy."""
        if not self._cache:
            return

        if self.policy == CachePolicy.LRU:
            # Remove oldest (first) item
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        elif self.policy == CachePolicy.LFU:
            # Remove least frequently used item
            min_access_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[min_access_key]
        elif self.policy == CachePolicy.FIFO:
            # Remove first inserted item
            self._cache.popitem(last=False)
        else:
            # Default to LRU
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with statistics including hit rate and utilization
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / max(total_requests, 1)

            return {
                **self._stats,
                "hit_rate": hit_rate,
                "size": len(self._cache),
                "max_size": self.max_size,
                "utilization": len(self._cache) / max(self.max_size, 1),
            }