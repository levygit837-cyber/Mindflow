"""Result caching for MindFlow tools.

Provides intelligent caching with TTL expiration, cache invalidation,
and size limits to improve tool performance.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ============================================================================
# Cache Entry
# ============================================================================

@dataclass
class CacheEntry:
    """A single cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: float | None
    size_bytes: int

    def is_expired(self) -> bool:
        """Check if entry has expired.

        Returns:
            True if expired, False otherwise
        """
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """Update last accessed time and increment access count."""
        self.last_accessed = time.time()
        self.access_count += 1


# ============================================================================
# Result Cache
# ============================================================================

class ResultCache:
    """LRU cache with TTL expiration and size limits."""

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: float | None = 3600.0
    ):
        """Initialize result cache.

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl: Default TTL in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._total_size_bytes = 0

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create deterministic string representation
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)

        # Hash for consistent key length
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes.

        Args:
            value: Value to estimate

        Returns:
            Estimated size in bytes
        """
        try:
            # Try to serialize to JSON and measure
            json_str = json.dumps(value, default=str)
            return len(json_str.encode('utf-8'))
        except Exception:
            # Fallback: rough estimate
            return 1024  # 1KB default

    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check expiration
        if entry.is_expired():
            self.invalidate(key)
            return None

        # Update access metadata
        entry.touch()

        # Move to end (LRU)
        self._cache.move_to_end(key)

        _logger.debug(f"Cache hit: {key[:16]}... (access count: {entry.access_count})")
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (None = use default)
        """
        # Estimate size
        size_bytes = self._estimate_size(value)

        # Check if value is too large
        if size_bytes > self.max_memory_bytes:
            _logger.warning(
                f"Value too large to cache: {size_bytes} bytes "
                f"(max: {self.max_memory_bytes})"
            )
            return

        # Remove existing entry if present
        if key in self._cache:
            self.invalidate(key)

        # Evict entries if needed
        self._evict_if_needed(size_bytes)

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            ttl=ttl if ttl is not None else self.default_ttl,
            size_bytes=size_bytes
        )

        # Add to cache
        self._cache[key] = entry
        self._total_size_bytes += size_bytes

        _logger.debug(
            f"Cache set: {key[:16]}... "
            f"(size: {size_bytes} bytes, ttl: {entry.ttl}s)"
        )

    def _evict_if_needed(self, incoming_size: int) -> None:
        """Evict entries if cache is full.

        Args:
            incoming_size: Size of incoming entry
        """
        # Evict by count
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        # Evict by memory
        while (
            self._total_size_bytes + incoming_size > self.max_memory_bytes
            and len(self._cache) > 0
        ):
            self._evict_lru()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Get first (oldest) entry
        key, entry = self._cache.popitem(last=False)
        self._total_size_bytes -= entry.size_bytes

        _logger.debug(
            f"Cache evict (LRU): {key[:16]}... "
            f"(access count: {entry.access_count})"
        )

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry.

        Args:
            key: Cache key

        Returns:
            True if entry was removed, False if not found
        """
        if key not in self._cache:
            return False

        entry = self._cache.pop(key)
        self._total_size_bytes -= entry.size_bytes

        _logger.debug(f"Cache invalidate: {key[:16]}...")
        return True

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all entries matching a pattern.

        Args:
            pattern: Pattern to match (substring)

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = [
            key for key in self._cache.keys()
            if pattern in key
        ]

        for key in keys_to_remove:
            self.invalidate(key)

        _logger.debug(f"Cache invalidate pattern '{pattern}': {len(keys_to_remove)} entries")
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._total_size_bytes = 0
        _logger.info(f"Cache cleared: {count} entries")

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        keys_to_remove = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in keys_to_remove:
            self.invalidate(key)

        if keys_to_remove:
            _logger.debug(f"Cache cleanup: {len(keys_to_remove)} expired entries")

        return len(keys_to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Statistics dict
        """
        total_accesses = sum(entry.access_count for entry in self._cache.values())

        return {
            "entries": len(self._cache),
            "max_size": self.max_size,
            "total_size_bytes": self._total_size_bytes,
            "max_memory_bytes": self.max_memory_bytes,
            "memory_usage_percent": (
                self._total_size_bytes / self.max_memory_bytes * 100
                if self.max_memory_bytes > 0 else 0
            ),
            "total_accesses": total_accesses,
            "default_ttl": self.default_ttl
        }


# ============================================================================
# Cache Decorator
# ============================================================================

def cached(
    cache: ResultCache | None = None,
    ttl: float | None = None,
    key_func: Callable | None = None
) -> Callable:
    """Decorator to cache function results.

    Args:
        cache: Cache instance (uses global if None)
        ttl: Optional TTL override
        key_func: Optional custom key generation function

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Get cache instance
            cache_instance = cache or get_global_cache()

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_instance._generate_key(
                    func.__name__, *args, **kwargs
                )

            # Try to get from cache
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache_instance.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# ============================================================================
# Global Cache
# ============================================================================

_global_cache: ResultCache | None = None


def get_global_cache() -> ResultCache:
    """Get global cache instance.

    Returns:
        ResultCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ResultCache()
    return _global_cache


def clear_global_cache() -> None:
    """Clear global cache."""
    cache = get_global_cache()
    cache.clear()


def get_cache_stats() -> dict[str, Any]:
    """Get global cache statistics.

    Returns:
        Statistics dict
    """
    cache = get_global_cache()
    return cache.get_stats()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "CacheEntry",
    "ResultCache",
    "cached",
    "get_global_cache",
    "clear_global_cache",
    "get_cache_stats",
]
