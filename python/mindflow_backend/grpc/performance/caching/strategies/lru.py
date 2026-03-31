"""LRU (Least Recently Used) cache eviction strategy.

Evicts the least recently accessed entries when cache is full.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from ..config import CacheConfig
from ..entry import CacheEntry
from .base import CacheStrategy


class LRUCacheStrategy(CacheStrategy):
    """Least Recently Used cache eviction strategy.

    Maintains entries in access order and evicts the least
    recently used entry when the cache reaches capacity.
    """

    def __init__(self, config: CacheConfig):
        """Initialize LRU cache strategy.

        Args:
            config: Cache configuration
        """
        super().__init__(config)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired_removals": 0,
        }

    def get(self, key: str) -> CacheEntry | None:
        """Get entry and move to end (most recent)."""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]

            # Check if expired
            if entry.is_expired:
                del self._cache[key]
                self._stats["expired_removals"] += 1
                return None

            # Move to end (most recent)
            self._cache.move_to_end(key)
            entry.touch()
            self._stats["hits"] += 1
            return entry

    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache, evicting LRU if necessary."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]

            # Evict if at capacity
            while len(self._cache) >= self.config.max_size:
                self._evict_lru()

            # Add new entry
            self._cache[key] = entry
            self._cache.move_to_end(key)
            return True

    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get number of entries."""
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            self._stats["expired_removals"] += len(expired_keys)
            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self.config.max_size,
                "hit_rate": self._stats["hits"] / max(total, 1),
            }

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._cache:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1