"""Advanced cache manager with multi-level hierarchy.

Provides L1 (memory) and L2 (Redis) cache hierarchy with
intelligent caching strategies, warming, and invalidation.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

from .backends import MemoryCacheBackend, RedisCacheBackend
from .models import CacheEntry, CacheLevel, CachePolicy

_logger = get_logger(__name__)


class CacheManager:
    """Advanced cache manager with multi-level hierarchy.

    Features:
    - L1 (memory) and L2 (Redis) cache levels
    - Intelligent cache warming
    - Cache invalidation strategies
    - Performance metrics
    - Cache analytics
    - Tag-based invalidation
    - Background cleanup
    """

    def __init__(self):
        """Initialize cache manager."""
        self._l1_cache: MemoryCacheBackend | None = None
        self._l2_cache: RedisCacheBackend | None = None
        self._enable_l1 = True
        self._enable_l2 = True
        self._default_ttl = 3600  # 1 hour
        self._max_ttl = 86400  # 24 hours
        self._background_cleanup_task: asyncio.Task | None = None
        self._is_running = False

        # Cache statistics
        self._stats = {
            "total_requests": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    async def initialize(self) -> None:
        """Initialize cache manager."""
        settings = get_settings()
        cache_config = settings.cache

        # Initialize L1 cache
        if cache_config.enable_l1_cache:
            self._l1_cache = MemoryCacheBackend(
                max_size=cache_config.l1_cache_size,
                policy=CachePolicy.LRU,
            )
            self._enable_l1 = True
        else:
            self._enable_l1 = False

        # Initialize L2 cache
        if cache_config.enable_l2_cache:
            self._l2_cache = RedisCacheBackend(key_prefix="cache:l2:")
            self._enable_l2 = True
        else:
            self._enable_l2 = False

        # Set default TTLs
        self._default_ttl = cache_config.default_ttl
        self._max_ttl = cache_config.max_ttl

        # Start background cleanup
        await self.start_background_cleanup()

        _logger.info(
            "cache_manager_initialized",
            l1_enabled=self._enable_l1,
            l2_enabled=self._enable_l2,
            default_ttl=self._default_ttl,
            l1_size=cache_config.l1_cache_size if self._enable_l1 else 0,
        )

    async def close(self) -> None:
        """Close cache manager."""
        await self.stop_background_cleanup()
        _logger.info("cache_manager_closed")

    async def get(self, key: str) -> Any | None:
        """Get value from cache hierarchy.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        self._stats["total_requests"] += 1

        # Try L1 cache first
        if self._enable_l1 and self._l1_cache:
            entry = await self._l1_cache.get(key)
            if entry:
                self._stats["l1_hits"] += 1
                return entry.value

        # Try L2 cache
        if self._enable_l2 and self._l2_cache:
            entry = await self._l2_cache.get(key)
            if entry:
                self._stats["l2_hits"] += 1

                # Promote to L1 cache
                if self._enable_l1 and self._l1_cache:
                    await self._l1_cache.set(key, entry)

                return entry.value

        self._stats["misses"] += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        tags: dict[str, str] | None = None,
    ) -> bool:
        """Set value in cache hierarchy.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Optional tags for the entry

        Returns:
            True if successful
        """
        # Validate TTL
        if ttl is None:
            ttl = self._default_ttl
        elif ttl > self._max_ttl:
            ttl = self._max_ttl

        # Create cache entry
        entry = CacheEntry(
            value=value,
            ttl=ttl,
            tags=tags or {},
            size_bytes=self._estimate_size(value),
        )

        success = True

        # Set in L1 cache
        if self._enable_l1 and self._l1_cache:
            success &= await self._l1_cache.set(key, entry)

        # Set in L2 cache
        if self._enable_l2 and self._l2_cache:
            success &= await self._l2_cache.set(key, entry)

        if success:
            self._stats["sets"] += 1

        return success

    async def delete(self, key: str) -> bool:
        """Delete value from cache hierarchy.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        success = True

        # Delete from L1 cache
        if self._enable_l1 and self._l1_cache:
            success &= await self._l1_cache.delete(key)

        # Delete from L2 cache
        if self._enable_l2 and self._l2_cache:
            success &= await self._l2_cache.delete(key)

        if success:
            self._stats["deletes"] += 1

        return success

    async def clear(self, level: CacheLevel | None = None) -> bool:
        """Clear cache entries.

        Args:
            level: Specific level to clear (all if None)

        Returns:
            True if successful
        """
        success = True

        if level is None or level == CacheLevel.L1_MEMORY:
            if self._enable_l1 and self._l1_cache:
                success &= await self._l1_cache.clear()

        if level is None or level == CacheLevel.L2_REDIS:
            if self._enable_l2 and self._l2_cache:
                success &= await self._l2_cache.clear()

        return success

    async def invalidate_by_tag(self, tag: str, value: str | None = None) -> int:
        """Invalidate cache entries by tag.

        Args:
            tag: Tag to invalidate
            value: Optional tag value to match

        Returns:
            Number of invalidated entries
        """
        invalidated = 0

        # Invalidate from L1 cache
        if self._enable_l1 and self._l1_cache:
            keys = await self._l1_cache.keys("*")
            for key in keys:
                entry = await self._l1_cache.get(key)
                if entry and tag in entry.tags:
                    if value is None or entry.tags.get(tag) == value:
                        await self._l1_cache.delete(key)
                        invalidated += 1

        # Invalidate from L2 cache
        if self._enable_l2 and self._l2_cache:
            keys = await self._l2_cache.keys("*")
            for key in keys:
                entry = await self._l2_cache.get(key)
                if entry and tag in entry.tags:
                    if value is None or entry.tags.get(tag) == value:
                        await self._l2_cache.delete(key)
                        invalidated += 1

        _logger.info(
            "cache_invalidated_by_tag",
            tag=tag,
            value=value,
            invalidated_count=invalidated,
        )

        return invalidated

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:
            Cache statistics
        """
        stats = self._stats.copy()

        # Calculate hit rates
        total_requests = stats["total_requests"]
        stats["hit_rate"] = (stats["l1_hits"] + stats["l2_hits"]) / max(total_requests, 1)
        stats["l1_hit_rate"] = stats["l1_hits"] / max(total_requests, 1)
        stats["l2_hit_rate"] = stats["l2_hits"] / max(total_requests, 1)

        # Add backend stats
        if self._enable_l1 and self._l1_cache:
            stats["l1_backend"] = self._l1_cache.get_stats()

        if self._enable_l2 and self._l2_cache:
            stats["l2_backend"] = self._l2_cache.get_stats()

        return stats

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes.

        Args:
            value: Value to estimate

        Returns:
            Estimated size in bytes
        """
        try:
            if isinstance(value, str):
                return len(value.encode("utf-8"))
            elif isinstance(value, (int, float, bool)):
                return 8
            elif isinstance(value, dict):
                return len(json.dumps(value).encode("utf-8"))
            elif isinstance(value, list):
                return sum(self._estimate_size(item) for item in value)
            elif isinstance(value, bytes):
                return len(value)
            else:
                return len(str(value).encode("utf-8"))
        except Exception:
            return 1024  # Default size

    async def start_background_cleanup(self) -> None:
        """Start background cleanup task."""
        if self._is_running:
            return

        self._is_running = True
        self._background_cleanup_task = asyncio.create_task(self._cleanup_loop())

        _logger.info("cache_background_cleanup_started")

    async def stop_background_cleanup(self) -> None:
        """Stop background cleanup task."""
        if not self._is_running:
            return

        self._is_running = False
        if self._background_cleanup_task:
            self._background_cleanup_task.cancel()
            try:
                await self._background_cleanup_task
            except asyncio.CancelledError:
                pass

        _logger.info("cache_background_cleanup_stopped")

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self._is_running:
            try:
                await self._cleanup_expired_entries()
                await asyncio.sleep(300)  # Cleanup every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("cache_cleanup_loop_error", error=str(e))
                await asyncio.sleep(60)  # Brief pause before retry

    async def _cleanup_expired_entries(self) -> None:
        """Clean up expired entries."""
        cleaned = 0

        # Clean L1 cache
        if self._enable_l1 and self._l1_cache:
            keys = await self._l1_cache.keys("*")
            for key in keys:
                entry = await self._l1_cache.get(key)
                if entry and entry.is_expired:
                    await self._l1_cache.delete(key)
                    cleaned += 1

        # Clean L2 cache (Redis handles TTL automatically, but we can clean invalid entries)
        if self._enable_l2 and self._l2_cache:
            # Redis handles TTL automatically, so no need for manual cleanup
            pass

        if cleaned > 0:
            _logger.debug("cache_cleanup_completed", cleaned_entries=cleaned)


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance.

    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager