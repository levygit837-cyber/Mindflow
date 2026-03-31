"""Size-based cache eviction strategy.

Evicts entries based on total memory usage.
"""

from __future__ import annotations

from typing import Any

from ..config import CacheConfig
from ..entry import CacheEntry
from .base import CacheStrategy


class SizeBasedCacheStrategy(CacheStrategy):
    """Size-based cache eviction strategy.

    Evicts entries when total memory usage exceeds the configured limit.
    """

    def __init__(self, config: CacheConfig):
        """Initialize size-based cache strategy.

        Args:
            config: Cache configuration
        """
        super().__init__(config)
        self._cache: dict[str, CacheEntry] = {}
        self._current_size_bytes: int = 0
        self._max_size_bytes: int = config.max_memory_mb * 1024 * 1024
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired_removals": 0,
        }

    def get(self, key: str) -> CacheEntry | None:
        """Get entry from cache."""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]

            # Check if expired
            if entry.is_expired:
                self._current_size_bytes -= entry.size_bytes
                del self._cache[key]
                self._stats["expired_removals"] += 1
                return None

            entry.touch()
            self._stats["hits"] += 1
            return entry

    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache, evicting if necessary."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_size_bytes -= old_entry.size_bytes
                del self._cache[key]

            # Evict entries until we have space
            while (
                self._current_size_bytes + entry.size_bytes > self._max_size_bytes
                and self._cache
            ):
                self._evict_largest()

            # Add new entry
            self._cache[key] = entry
            self._current_size_bytes += entry.size_bytes
            return True

    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._current_size_bytes -= entry.size_bytes
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._current_size_bytes = 0

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
                entry = self._cache[key]
                self._current_size_bytes -= entry.size_bytes
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
                "current_size_bytes": self._current_size_bytes,
                "max_size_bytes": self._max_size_bytes,
                "utilization": self._current_size_bytes / max(self._max_size_bytes, 1),
                "hit_rate": self._stats["hits"] / max(total, 1),
            }

    def _evict_largest(self) -> None:
        """Evict the largest entry."""
        if self._cache:
            largest_key = max(
                self._cache.keys(),
                key=lambda k: self._cache[k].size_bytes,
            )
            entry = self._cache[largest_key]
            self._current_size_bytes -= entry.size_bytes
            del self._cache[largest_key]
            self._stats["evictions"] += 1