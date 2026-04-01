"""Unit tests for result caching module.

Tests cache operations, LRU eviction, TTL expiration, and invalidation.
"""

from __future__ import annotations

import time

import pytest

from mindflow_backend.agents.tools.caching.result_cache import (
    CacheEntry,
    ResultCache,
    cached,
    clear_global_cache,
    get_cache_stats,
    get_global_cache,
)


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "value"},
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            ttl=3600.0,
            size_bytes=100
        )

        assert entry.key == "test_key"
        assert entry.value["data"] == "value"
        assert entry.ttl == 3600.0

    def test_entry_not_expired(self):
        """Test entry is not expired."""
        entry = CacheEntry(
            key="test_key",
            value="value",
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            ttl=3600.0,
            size_bytes=10
        )

        assert entry.is_expired() is False

    def test_entry_expired(self):
        """Test entry is expired."""
        entry = CacheEntry(
            key="test_key",
            value="value",
            created_at=time.time() - 3700,  # Created over an hour ago
            last_accessed=time.time(),
            access_count=0,
            ttl=3600.0,  # 1 hour TTL
            size_bytes=10
        )

        assert entry.is_expired() is True

    def test_entry_no_ttl(self):
        """Test entry with no TTL never expires."""
        entry = CacheEntry(
            key="test_key",
            value="value",
            created_at=time.time() - 86400,  # Created a day ago
            last_accessed=time.time(),
            access_count=0,
            ttl=None,  # No expiration
            size_bytes=10
        )

        assert entry.is_expired() is False

    def test_entry_touch(self):
        """Test touching an entry."""
        entry = CacheEntry(
            key="test_key",
            value="value",
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            ttl=None,
            size_bytes=10
        )

        initial_access_count = entry.access_count
        initial_last_accessed = entry.last_accessed

        time.sleep(0.01)
        entry.touch()

        assert entry.access_count == initial_access_count + 1
        assert entry.last_accessed > initial_last_accessed


class TestResultCache:
    """Test ResultCache class."""

    @pytest.fixture
    def cache(self):
        """Create test cache."""
        return ResultCache(max_size=10, max_memory_mb=1, default_ttl=3600.0)

    def test_cache_creation(self):
        """Test creating a cache."""
        cache = ResultCache(max_size=100, max_memory_mb=10, default_ttl=1800.0)

        assert cache.max_size == 100
        assert cache.max_memory_bytes == 10 * 1024 * 1024
        assert cache.default_ttl == 1800.0

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        cache.set("key1", {"data": "value1"})
        value = cache.get("key1")

        assert value is not None
        assert value["data"] == "value1"

    def test_get_nonexistent_key(self, cache):
        """Test getting nonexistent key."""
        value = cache.get("nonexistent")
        assert value is None

    def test_get_expired_entry(self):
        """Test getting expired entry."""
        cache = ResultCache(default_ttl=0.1)  # 100ms TTL

        cache.set("key1", "value1")
        assert cache.get("key1") is not None

        time.sleep(0.2)  # Wait for expiration

        assert cache.get("key1") is None

    def test_set_with_custom_ttl(self):
        """Test setting with custom TTL."""
        cache = ResultCache(default_ttl=3600.0)

        cache.set("key1", "value1", ttl=0.1)  # 100ms TTL

        assert cache.get("key1") is not None
        time.sleep(0.2)
        assert cache.get("key1") is None

    def test_lru_eviction_by_count(self, cache):
        """Test LRU eviction when max_size is reached."""
        # Fill cache to max_size
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        # Access key0 to make it recently used
        cache.get("key0")

        # Add new entry - should evict key1 (least recently used)
        cache.set("key10", "value10")

        assert cache.get("key0") is not None  # Still there
        assert cache.get("key1") is None      # Evicted
        assert cache.get("key10") is not None  # New entry

    def test_lru_eviction_by_memory(self):
        """Test LRU eviction when memory limit is reached."""
        cache = ResultCache(max_size=100, max_memory_mb=0.001)  # Very small memory

        # Add entries until memory limit is hit
        cache.set("key1", "x" * 500)
        cache.set("key2", "x" * 500)

        # key1 should be evicted due to memory pressure
        stats = cache.get_stats()
        assert stats["entries"] < 2

    def test_invalidate_single_key(self, cache):
        """Test invalidating single key."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None
        assert cache.get("key2") is not None

    def test_invalidate_nonexistent_key(self, cache):
        """Test invalidating nonexistent key."""
        assert cache.invalidate("nonexistent") is False

    def test_invalidate_pattern(self, cache):
        """Test invalidating by pattern."""
        cache.set("prefix_key1", "value1")
        cache.set("prefix_key2", "value2")
        cache.set("other_key", "value3")

        count = cache.invalidate_pattern("prefix_")

        assert count == 2
        assert cache.get("prefix_key1") is None
        assert cache.get("prefix_key2") is None
        assert cache.get("other_key") is not None

    def test_clear(self, cache):
        """Test clearing all entries."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        stats = cache.get_stats()
        assert stats["entries"] == 0

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = ResultCache(default_ttl=0.1)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        time.sleep(0.2)  # Wait for expiration

        count = cache.cleanup_expired()

        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_get_stats(self, cache):
        """Test getting cache statistics."""
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        stats = cache.get_stats()

        assert stats["entries"] == 2
        assert stats["max_size"] == 10
        assert stats["total_size_bytes"] > 0
        assert stats["memory_usage_percent"] > 0
        assert stats["default_ttl"] == 3600.0

    def test_value_too_large(self):
        """Test that very large values are rejected."""
        cache = ResultCache(max_memory_mb=0.001)  # 1KB limit

        # Try to cache 10KB value
        large_value = "x" * 10000

        cache.set("key1", large_value)

        # Should be rejected
        assert cache.get("key1") is None


class TestCachedDecorator:
    """Test @cached decorator."""

    def test_cached_decorator_basic(self):
        """Test basic cached decorator usage."""
        cache = ResultCache()
        call_count = 0

        @cached(cache=cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - executes function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - returns cached result
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

    def test_cached_decorator_different_args(self):
        """Test cached decorator with different arguments."""
        cache = ResultCache()
        call_count = 0

        @cached(cache=cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count == 2  # Called twice for different args

    def test_cached_decorator_with_ttl(self):
        """Test cached decorator with TTL."""
        cache = ResultCache()
        call_count = 0

        @cached(cache=cache, ttl=0.1)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        assert call_count == 1

        time.sleep(0.2)  # Wait for expiration

        result2 = expensive_function(5)
        assert call_count == 2  # Called again after expiration


class TestGlobalCache:
    """Test global cache functions."""

    def test_get_global_cache(self):
        """Test getting global cache instance."""
        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2  # Same instance

    def test_clear_global_cache(self):
        """Test clearing global cache."""
        cache = get_global_cache()
        cache.set("key1", "value1")

        clear_global_cache()

        assert cache.get("key1") is None

    def test_get_cache_stats_global(self):
        """Test getting global cache stats."""
        cache = get_global_cache()
        cache.clear()
        cache.set("key1", "value1")

        stats = get_cache_stats()

        assert stats["entries"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
