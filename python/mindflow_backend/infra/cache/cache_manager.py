"""Advanced cache manager with multi-level hierarchy.

Provides L1 (memory) and L2 (Redis) cache hierarchy with
intelligent caching strategies, warming, and invalidation.
"""

from __future__ import annotations

import asyncio
import time
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from datetime import datetime, UTC, timedelta
from enum import Enum
from collections import OrderedDict
import threading
import json

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.cache.redis_client import get_redis_client
from mindflow_backend.infra.config import get_settings

_logger = get_logger(__name__)

T = TypeVar('T')


class CacheLevel(Enum):
    """Cache levels in the hierarchy."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"


class CachePolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return (datetime.now(UTC) - self.created_at).total_seconds() > self.ttl
        
    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return (datetime.now(UTC) - self.created_at).total_seconds()
        
    def touch(self) -> None:
        """Update last access time and count."""
        self.last_accessed = datetime.now(UTC)
        self.access_count += 1


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry."""
        pass
        
    @abstractmethod
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry."""
        pass
        
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cache entry."""
        pass
        
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass
        
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass
        
    @abstractmethod
    async def size(self) -> int:
        """Get cache size."""
        pass


class MemoryCacheBackend(CacheBackend):
    """L1 Memory cache backend with LRU eviction."""
    
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
        """Get cache entry from memory."""
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
        """Set cache entry in memory."""
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
        """Delete cache entry from memory."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
                return True
            return False
            
    async def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            return True
            
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        with self._lock:
            import fnmatch
            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]
            
    async def size(self) -> int:
        """Get cache size."""
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
        """Get cache statistics."""
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


class RedisCacheBackend(CacheBackend):
    """L2 Redis cache backend."""
    
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
            Full Redis key
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
        """Get cache entry from Redis."""
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
        """Set cache entry in Redis."""
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
        """Delete cache entry from Redis."""
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
        """Clear all cache entries."""
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
        """Get keys matching pattern."""
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
        """Get cache size."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self._redis_client.keys(pattern)
            return len(keys)
            
        except Exception as e:
            self._stats["errors"] += 1
            _logger.error("redis_cache_size_failed", error=str(e))
            return 0
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / max(total_requests, 1)
        
        return {
            **self._stats,
            "hit_rate": hit_rate,
        }


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
        self._l1_cache: Optional[MemoryCacheBackend] = None
        self._l2_cache: Optional[RedisCacheBackend] = None
        self._enable_l1 = True
        self._enable_l2 = True
        self._default_ttl = 3600  # 1 hour
        self._max_ttl = 86400  # 24 hours
        self._background_cleanup_task: Optional[asyncio.Task] = None
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
                policy=CachePolicy.LRU
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
        
    async def get(self, key: str) -> Optional[Any]:
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
        ttl: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None
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
        
    async def clear(self, level: Optional[CacheLevel] = None) -> bool:
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
        
    async def invalidate_by_tag(self, tag: str, value: Optional[str] = None) -> int:
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
        
    async def get_stats(self) -> Dict[str, Any]:
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
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float, bool)):
                return 8
            elif isinstance(value, dict):
                return len(json.dumps(value).encode('utf-8'))
            elif isinstance(value, list):
                return sum(self._estimate_size(item) for item in value)
            elif isinstance(value, bytes):
                return len(value)
            else:
                return len(str(value).encode('utf-8'))
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
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance.
    
    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
