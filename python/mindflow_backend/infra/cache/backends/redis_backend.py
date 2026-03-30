"""L2 Redis cache backend.

Provides Redis-based caching with automatic serialization/deserialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.cache.redis_client import get_redis_client

from ..models import CacheEntry
from .base import CacheBackend

_logger = get_logger(__name__)


class RedisCacheBackend(CacheBackend):
    """L2 Redis cache backend.

    Provides distributed caching via Redis with automatic
    serialization and error handling.

    Attributes:
        key_prefix: Prefix for all cache keys
    """

    def __init__(self, key_prefix: str = "cache:"):
        """Initialize Redis cache backend.

        Args:
            key_prefix: Prefix for all cache keys
        """
        self.key_prefix = key_prefix
        self._redis_client = get_redis_client()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

    def _make_key(self, key: str) -> str:
        """Create full Redis key.

        Args:
            key: Cache key

        Returns:
            Full Redis key with prefix
        """
        return f"{self.key_prefix}{key}"

    def _serialize_entry(self, entry: CacheEntry) -> Dict[str, Any]:
        """Serialize cache entry for Redis.

        Args:
            entry: Cache entry

        Returns:
            Serialized entry data
        """
        return {
            "value": entry.value,
            "created_at": entry.created_at.isoformat(),
            "last_accessed": entry.last_accessed.isoformat(),
            "access_count": entry.access_count,
            "ttl": entry.ttl,
            "size_bytes": entry.size_bytes,
            "tags": entry.tags,
        }

    def _deserialize_entry(self, data: Dict[str, Any]) -> CacheEntry:
        """Deserialize cache entry from Redis.

        Args:
            data: Serialized entry data

        Returns:
            Cache entry
        """
        return CacheEntry(
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data["access_count"],
            ttl=data.get("ttl"),
            size_bytes=data.get("size_bytes", 0),
            tags=data.get("tags", {}),
        )

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry from Redis.

        Args:
            key: Cache key

        Returns:
            Cache entry or None if not found/expired
        """
        try:
            redis_key = self._make_key(key)
            data = await self._redis_client.get(redis_key)

            if data is None:
                self._stats["misses"] += 1
                return None

            entry = self._deserialize_entry(data)

            # Check expiration
            if entry.is_expired:
                await self.delete(key)
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return entry

        except Exception as e:
            self._stats["errors"] += 1
            _logger.error("redis_cache_get_failed", key=key, error=str(e))
            return None

    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry in Redis.

        Args:
            key: Cache key
            entry: Cache entry to store

        Returns:
            True if successful
        """
        try:
            redis_key = self._make_key(key)
            data = self._serialize_entry(entry)

            # Set TTL if specified
            ttl = entry.ttl
            success = await self._redis_client.set(redis_key, data, ttl=ttl)

            if success:
                self._stats["sets"] += 1

            return success

        except Exception as e:
            self._stats["errors"] += 1
            _logger.error("redis_cache_set_failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete cache entry from Redis.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        try:
            redis_key = self._make_key(key)
            success = await self._redis_client.delete(redis_key)

            if success:
                self._stats["deletes"] += 1

            return success

        except Exception as e:
            self._stats["errors"] += 1
            _logger.error("redis_cache_delete_failed", key=key, error=str(e))
            return False

    async def clear(self) -> bool:
        """Clear all cache entries.

        Returns:
            True if successful
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self._redis_client.keys(pattern)

            if keys:
                await self._redis_client.delete(*keys)

            return True

        except Exception as e:
            self._stats["errors"] += 1
            _logger.error("redis_cache_clear_failed", error=str(e))
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern.

        Args:
            pattern: Glob pattern for key matching

        Returns:
            List of matching keys (without prefix)
        """
        try:
            redis_pattern = f"{self.key_prefix}{pattern}"
            redis_keys = await self._redis_client.keys(redis_pattern)

            # Remove prefix from keys
            prefix_len = len(self.key_prefix)
            return [key[prefix_len:] for key in redis_keys]

        except Exception as e:
            self._stats["errors"] += 1
            _logger.error("redis_cache_keys_failed", pattern=pattern, error=str(e))
            return []

    async def size(self) -> int:
        """Get number of entries in cache.

        Returns:
            Number of entries
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self._redis_client.keys(pattern)
            return len(keys)

        except Exception as e:
            self._stats["errors"] += 1
            _logger.error("redis_cache_size_failed", error=str(e))
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with statistics including hit rate
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / max(total_requests, 1)

        return {
            **self._stats,
            "hit_rate": hit_rate,
        }