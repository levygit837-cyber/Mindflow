"""TTL (Time To Live) cache eviction strategy.

Evicts entries based on their expiration time.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ..config import CacheConfig
from ..entry import CacheEntry
from .base import CacheStrategy


class TTLCacheStrategy(CacheStrategy):
    """Time To Live cache eviction strategy.

    Automatically evicts entries after their TTL expires.
    """

    def __init__(self, config: CacheConfig):
        """Initialize TTL cache strategy.

        Args:
            config: Cache configuration
        """
        super().__init__(config)
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired_removals": 0,
        }

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry if not expired."""
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

            entry.touch()
            self._stats["hits"] += 1
            return entry

    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]

            # Clean up expired entries before adding
            self.cleanup_expired()

            # Evict if still at capacity
            while len(self._cache) >= self.config.max_size:
                self._evict_oldest()

            # Add new entry
            self._cache[key] = entry
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

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self.config.max_size,
                "hit_rate": self._stats["hits"] / max(total, 1),
            }

    def _evict_oldest(self) -> None:
        """Evict the oldest entry."""
        if self._cache:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at,
            )
            del self._cache[oldest_key]
            self._stats["evictions"] += 1