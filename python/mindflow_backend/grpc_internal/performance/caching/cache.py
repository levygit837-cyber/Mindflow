"""gRPC response cache with multiple eviction strategies.

Provides intelligent caching for gRPC responses to reduce
latency and server load for frequently accessed data.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger

from .config import CacheConfig, CacheEvictionPolicy
from .entry import CacheEntry
from .strategies import (
    CacheStrategy,
    LRUCacheStrategy,
    SizeBasedCacheStrategy,
    TTLCacheStrategy,
)

_logger = get_logger(__name__)


class GrpcResponseCache:
    """Main gRPC response cache with strategy selection.

    Provides intelligent caching for gRPC responses with support for
    multiple eviction strategies (LRU, TTL, SizeBased).
    """

    def __init__(self, config: CacheConfig | None = None):
        """Initialize gRPC response cache.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._strategy = self._create_strategy()
        self._cleanup_thread = None
        self._running = False

        _logger.info(
            "grpc_cache_initialized",
            strategy=self.config.eviction_policy.value,
            max_size=self.config.max_size,
            max_memory_mb=self.config.max_memory_mb,
        )

    def _create_strategy(self) -> CacheStrategy:
        """Create cache strategy based on configuration.

        Returns:
            Cache strategy instance
        """
        if self.config.eviction_policy == CacheEvictionPolicy.LRU:
            return LRUCacheStrategy(self.config)
        elif self.config.eviction_policy == CacheEvictionPolicy.TTL:
            return TTLCacheStrategy(self.config)
        elif self.config.eviction_policy == CacheEvictionPolicy.SIZE_BASED:
            return SizeBasedCacheStrategy(self.config)
        else:
            raise ValueError(f"Unsupported eviction policy: {self.config.eviction_policy}")

    def get(self, key: str) -> bytes | None:
        """Get cached response.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.config.enabled:
            return None

        entry = self._strategy.get(key)
        return entry.value if entry else None

    def put(
        self,
        key: str,
        value: bytes,
        ttl_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Cache a response.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            metadata: Optional metadata

        Returns:
            True if successful
        """
        if not self.config.enabled:
            return False

        # Use default TTL if not provided
        if ttl_seconds is None:
            ttl_seconds = self.config.default_ttl_seconds
        elif ttl_seconds > self.config.max_ttl_seconds:
            ttl_seconds = self.config.max_ttl_seconds

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

        return self._strategy.put(key, entry)

    def remove(self, key: str) -> bool:
        """Remove cached response.

        Args:
            key: Cache key

        Returns:
            True if removed
        """
        return self._strategy.remove(key)

    def clear(self) -> None:
        """Clear all cached responses."""
        self._strategy.clear()
        _logger.info("grpc_cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with statistics
        """
        stats = self._strategy.get_stats()
        stats["enabled"] = self.config.enabled
        stats["strategy"] = self.config.eviction_policy.value
        return stats

    def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed
        """
        return self._strategy.cleanup_expired()

    def start_background_cleanup(self) -> None:
        """Start background cleanup thread."""
        if self._running or not self.config.enabled:
            return

        import threading

        def cleanup_worker():
            self._running = True
            _logger.info("grpc_cache_cleanup_started")

            while self._running:
                try:
                    removed = self.cleanup_expired()

                    if removed > 0:
                        _logger.debug("grpc_cache_cleanup_completed", removed=removed)

                    # Sleep for cleanup interval
                    time.sleep(self.config.cleanup_interval_seconds)

                except Exception as e:
                    _logger.error("grpc_cache_cleanup_error", error=str(e))
                    time.sleep(self.config.cleanup_interval_seconds)

        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()

    def stop_background_cleanup(self) -> None:
        """Stop background cleanup thread."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
            _logger.info("grpc_cache_cleanup_stopped")

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching pattern.

        Args:
            pattern: Pattern to match (prefix)

        Returns:
            Number of entries removed
        """
        # This would require pattern matching capability
        # For now, implement simple prefix matching
        if hasattr(self._strategy, "_cache"):
            keys_to_remove = [
                key for key in self._strategy._cache.keys()
                if key.startswith(pattern)
            ]

            removed = 0
            for key in keys_to_remove:
                if self._strategy.remove(key):
                    removed += 1

            _logger.info("grpc_cache_pattern_invalidated", pattern=pattern, removed=removed)
            return removed

        return 0

    def update_config(self, new_config: CacheConfig) -> None:
        """Update cache configuration.

        Args:
            new_config: New cache configuration
        """
        self.config = new_config

        # Recreate strategy if eviction policy changed
        old_strategy = type(self._strategy).__name__
        new_strategy = self._create_strategy()

        if old_strategy != type(new_strategy).__name__:
            # Transfer existing cache data if possible
            _logger.info(
                "grpc_cache_strategy_changed",
                old=old_strategy,
                new=type(new_strategy).__name__,
            )

        self._strategy = new_strategy
        _logger.info("grpc_cache_config_updated")

    def __del__(self):
        """Cleanup on deletion."""
        self.stop_background_cleanup()