"""gRPC response cache with multiple eviction strategies.

Provides intelligent caching for gRPC responses to reduce
latency and server load for frequently accessed data.
"""

from __future__ import annotations

import time
import hashlib
import json
from typing import Dict, Any, Optional, Union, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict
from abc import ABC, abstractmethod
import threading

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CacheEvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"
    TTL = "ttl"
    SIZE_BASED = "size_based"
    LFU = "lfu"


@dataclass
class CacheConfig:
    """Configuration for response caching."""
    
    # Basic settings
    enabled: bool = True
    max_size: int = 1000  # Maximum number of entries
    max_memory_mb: int = 100  # Maximum memory usage in MB
    
    # TTL settings
    default_ttl_seconds: int = 300  # 5 minutes default
    max_ttl_seconds: int = 3600  # 1 hour maximum
    
    # Eviction policy
    eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU
    
    # Cache key settings
    key_prefix: str = "grpc_cache"
    include_method: bool = True
    include_request_hash: bool = True
    include_metadata: bool = False
    
    # Performance settings
    enable_stats: bool = True
    cleanup_interval_seconds: int = 60
    max_cleanup_time_ms: float = 10.0
    
    # Cache invalidation
    auto_invalidate_on_error: bool = True
    invalidate_on_config_change: bool = True
    
    # Content-based caching
    cacheable_content_types: List[str] = field(default_factory=lambda: [
        "application/json",
        "application/x-protobuf",
        "text/plain"
    ])
    
    # Size thresholds
    min_cacheable_size_bytes: int = 1
    max_cacheable_size_bytes: int = 10 * 1024 * 1024  # 10MB
    
    def should_cache_response(self, response_data: bytes, content_type: str = "") -> bool:
        """Determine if response should be cached."""
        if not self.enabled:
            return False
        
        # Check size constraints
        size = len(response_data)
        if size < self.min_cacheable_size_bytes or size > self.max_cacheable_size_bytes:
            return False
        
        # Check content type
        if content_type and content_type not in self.cacheable_content_types:
            return False
        
        return True
    
    def generate_cache_key(self, method: str, request_data: bytes, 
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for request."""
        key_parts = [self.key_prefix]
        
        if self.include_method:
            key_parts.append(method)
        
        if self.include_request_hash:
            request_hash = hashlib.md5(request_data).hexdigest()
            key_parts.append(request_hash)
        
        if self.include_metadata and metadata:
            metadata_hash = hashlib.md5(
                json.dumps(metadata, sort_keys=True).encode()
            ).hexdigest()
            key_parts.append(metadata_hash)
        
        return ":".join(key_parts)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    
    key: str
    value: bytes
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = len(self.value)
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at
    
    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheStrategy(ABC):
    """Base class for cache eviction strategies."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        raise NotImplementedError
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache."""
        raise NotImplementedError
    
    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        raise NotImplementedError
    
    def clear(self) -> None:
        """Clear all entries."""
        raise NotImplementedError
    
    def size(self) -> int:
        """Get number of entries."""
        raise NotImplementedError
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        raise NotImplementedError


class LRUCacheStrategy(CacheStrategy):
    """Least Recently Used cache eviction strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_removals': 0,
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry and move to end (most recently used)."""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired:
                del self._cache[key]
                self._stats['expired_removals'] += 1
                return None
            
            # Move to end (most recently used)
            entry.touch()
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            
            return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Check size limit
            while len(self._cache) >= self.config.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
            
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
                self._stats['expired_removals'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            
            return {
                'entries': len(self._cache),
                'max_entries': self.config.max_size,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate_percent': hit_rate,
                'evictions': self._stats['evictions'],
                'expired_removals': self._stats['expired_removals'],
            }


class TTLCacheStrategy(CacheStrategy):
    """Time-To-Live cache eviction strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'expired_removals': 0,
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry if not expired."""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired:
                del self._cache[key]
                self._stats['expired_removals'] += 1
                return None
            
            entry.touch()
            self._stats['hits'] += 1
            return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache."""
        with self._lock:
            # Check size limit
            if len(self._cache) >= self.config.max_size:
                # Remove oldest entry (simple FIFO for TTL)
                oldest_key = min(self._cache.keys(), 
                              key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]
            
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
                self._stats['expired_removals'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            
            return {
                'entries': len(self._cache),
                'max_entries': self.config.max_size,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate_percent': hit_rate,
                'expired_removals': self._stats['expired_removals'],
            }


class SizeBasedCacheStrategy(CacheStrategy):
    """Size-based cache eviction strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._cache: Dict[str, CacheEntry] = {}
        self._current_size_bytes = 0
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            entry.touch()
            self._stats['hits'] += 1
            return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache, enforcing size limits."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_size_bytes -= old_entry.size_bytes
                del self._cache[key]
            
            # Check memory limit
            max_memory_bytes = self.config.max_memory_mb * 1024 * 1024
            while (self._current_size_bytes + entry.size_bytes > max_memory_bytes and 
                   self._cache):
                # Remove smallest entry
                smallest_key = min(self._cache.keys(), 
                                 key=lambda k: self._cache[k].size_bytes)
                smallest_entry = self._cache[smallest_key]
                self._current_size_bytes -= smallest_entry.size_bytes
                del self._cache[smallest_key]
                self._stats['evictions'] += 1
            
            # Check entry count limit
            while len(self._cache) >= self.config.max_size:
                oldest_key = min(self._cache.keys(), 
                              key=lambda k: self._cache[k].created_at)
                oldest_entry = self._cache[oldest_key]
                self._current_size_bytes -= oldest_entry.size_bytes
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
            
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
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'entries': len(self._cache),
                'max_entries': self.config.max_size,
                'total_size_bytes': self._current_size_bytes,
                'total_size_mb': self._current_size_bytes / (1024 * 1024),
                'max_size_mb': self.config.max_memory_mb,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate_percent': hit_rate,
                'evictions': self._stats['evictions'],
            }


class GrpcResponseCache:
    """Main gRPC response cache with strategy selection."""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._strategy = self._create_strategy()
        self._cleanup_thread = None
        self._running = False
        
        _logger.info(
            "grpc_cache_initialized",
            strategy=self.config.eviction_policy.value,
            max_size=self.config.max_size,
            max_memory_mb=self.config.max_memory_mb
        )
    
    def _create_strategy(self) -> CacheStrategy:
        """Create cache strategy based on configuration."""
        if self.config.eviction_policy == CacheEvictionPolicy.LRU:
            return LRUCacheStrategy(self.config)
        elif self.config.eviction_policy == CacheEvictionPolicy.TTL:
            return TTLCacheStrategy(self.config)
        elif self.config.eviction_policy == CacheEvictionPolicy.SIZE_BASED:
            return SizeBasedCacheStrategy(self.config)
        else:
            raise ValueError(f"Unsupported eviction policy: {self.config.eviction_policy}")
    
    def get(self, key: str) -> Optional[bytes]:
        """Get cached response."""
        if not self.config.enabled:
            return None
        
        entry = self._strategy.get(key)
        return entry.value if entry else None
    
    def put(self, key: str, value: bytes, ttl_seconds: Optional[float] = None,
           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Cache a response."""
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
            metadata=metadata or {}
        )
        
        return self._strategy.put(key, entry)
    
    def remove(self, key: str) -> bool:
        """Remove cached response."""
        return self._strategy.remove(key)
    
    def clear(self) -> None:
        """Clear all cached responses."""
        self._strategy.clear()
        _logger.info("grpc_cache_cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._strategy.get_stats()
        stats['enabled'] = self.config.enabled
        stats['strategy'] = self.config.eviction_policy.value
        return stats
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
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
                    start_time = time.time()
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
        """Invalidate entries matching pattern."""
        # This would require pattern matching capability
        # For now, implement simple prefix matching
        if hasattr(self._strategy, '_cache'):
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
        """Update cache configuration."""
        self.config = new_config
        
        # Recreate strategy if eviction policy changed
        old_strategy = type(self._strategy).__name__
        new_strategy = self._create_strategy()
        
        if old_strategy != type(new_strategy).__name__:
            # Transfer existing cache data if possible
            _logger.info(
                "grpc_cache_strategy_changed",
                old=old_strategy,
                new=type(new_strategy).__name__
            )
        
        self._strategy = new_strategy
        _logger.info("grpc_cache_config_updated")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop_background_cleanup()
