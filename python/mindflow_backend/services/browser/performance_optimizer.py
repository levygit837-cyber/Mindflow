"""Performance optimization for LightPanda browsers."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry."""

    key: str
    content: bytes
    content_type: str
    cached_at: datetime
    ttl: timedelta
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() - self.cached_at > self.ttl

    def increment_hit(self) -> None:
        """Increment hit count."""
        self.hit_count += 1


class PerformanceOptimizer:
    """Optimizes browser performance with caching and parallel operations."""

    def __init__(
        self,
        enable_cache: bool = True,
        cache_ttl_seconds: int = 3600,
        max_cache_size: int = 1000,
    ):
        """Initialize the performance optimizer.

        Args:
            enable_cache: Whether to enable caching
            cache_ttl_seconds: Cache time-to-live in seconds
            max_cache_size: Maximum cache size
        """
        self.enable_cache = enable_cache
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.max_cache_size = max_cache_size

        self._cache: dict[str, CacheEntry] = {}
        self._logger = get_logger(__name__)

        # Start cleanup loop automatically
        self._cleanup_task: asyncio.Task | None = None
        # Note: Background task will be started when async context is available
        # Caller should call start() method in async context

    async def start(self) -> None:
        """Start background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    def _generate_cache_key(self, url: str, method: str = "GET") -> str:
        """Generate cache key.

        Args:
            url: Request URL
            method: HTTP method

        Returns:
            str: Cache key
        """
        key_string = f"{method}:{url}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def get_cached(self, url: str, method: str = "GET") -> bytes | None:
        """Get cached content.

        Args:
            url: Request URL
            method: HTTP method

        Returns:
            bytes | None: Cached content or None
        """
        if not self.enable_cache:
            return None

        key = self._generate_cache_key(url, method)

        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                entry.increment_hit()
                self._logger.debug("cache_hit", url=url)
                return entry.content
            else:
                # Remove expired entry
                del self._cache[key]

        return None

    async def cache_response(
        self,
        url: str,
        content: bytes,
        content_type: str,
        method: str = "GET",
    ) -> None:
        """Cache response.

        Args:
            url: Request URL
            content: Response content
            content_type: Content type
            method: HTTP method
        """
        if not self.enable_cache:
            return

        # Check cache size limit
        if len(self._cache) >= self.max_cache_size:
            # Remove least recently used (simplified: oldest)
            oldest_key = min(
                self._cache.keys(), key=lambda k: self._cache[k].cached_at
            )
            del self._cache[oldest_key]

        key = self._generate_cache_key(url, method)
        entry = CacheEntry(
            key=key,
            content=content,
            content_type=content_type,
            cached_at=datetime.utcnow(),
            ttl=self.cache_ttl,
        )

        self._cache[key] = entry
        self._logger.debug("cache_set", url=url)

    async def execute_parallel(
        self,
        operations: list[callable],
        max_concurrency: int = 5,
) -> list[Any]:
        """Execute operations in parallel with concurrency control.

        Args:
            operations: List of operations to execute
            max_concurrency: Maximum concurrent operations

        Returns:
            list[Any]: Results
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def limited_operation(op):
            async with semaphore:
                return await op()

        results = await asyncio.gather(
            *[limited_operation(op) for op in operations],
            return_exceptions=True,
        )

        return results

    async def _cleanup_loop(self) -> None:
        """Loop for cache cleanup."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                expired_keys = [
                    key
                    for key, entry in self._cache.items()
                    if entry.is_expired()
                ]

                for key in expired_keys:
                    del self._cache[key]

                if expired_keys:
                    self._logger.info("cache_cleanup", count=len(expired_keys))

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._logger.error("cache_cleanup_error", error=str(exc))

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            dict[str, Any]: Cache statistics
        """
        total_hits = sum(entry.hit_count for entry in self._cache.values())

        return {
            "cache_size": len(self._cache),
            "max_cache_size": self.max_cache_size,
            "total_hits": total_hits,
            "cache_enabled": self.enable_cache,
        }
