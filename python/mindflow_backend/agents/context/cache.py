"""Cache implementation for context retrieval.

Provides thread-safe caching with TTL and size limits
for context retrieval operations.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional
from collections import OrderedDict

from mindflow_backend.agents.core.interfaces import Cache
from mindflow_backend.exceptions import AgentCacheError
from mindflow_backend.config.agents import get_agent_config


class LRUCache(Cache):
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int | None = None, default_ttl: int | None = None):
        self.max_size = max_size or get_agent_config().cache_size
        self.default_ttl = default_ttl or get_agent_config().cache_ttl_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if self._is_expired(entry):
                del self._cache[key]
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry["value"]
    
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        try:
            with self._lock:
                # Remove existing entry if present
                if key in self._cache:
                    del self._cache[key]
                
                # Enforce size limit
                while len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)  # Remove oldest
                
                # Add new entry
                ttl = ttl or self.default_ttl
                expire_time = time.time() + ttl if ttl > 0 else None
                
                self._cache[key] = {
                    "value": value,
                    "expire_time": expire_time,
                    "created_time": time.time(),
                }
                
                # Move to end
                self._cache.move_to_end(key)
        
        except Exception as e:
            raise AgentCacheError(f"Failed to set cache entry: {e}", operation="set", key=key)
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
        except Exception as e:
            raise AgentCacheError(f"Failed to delete cache entry: {e}", operation="delete", key=key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            with self._lock:
                self._cache.clear()
        except Exception as e:
            raise AgentCacheError(f"Failed to clear cache: {e}", operation="clear")
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if entry["expire_time"] is None:
            return False
        return time.time() > entry["expire_time"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values() 
                if self._is_expired(entry)
            )
            
            return {
                "total_entries": total_entries,
                "max_size": self.max_size,
                "expired_entries": expired_entries,
                "usage_ratio": total_entries / self.max_size if self.max_size > 0 else 0,
            }


class ContextCache:
    """Specialized cache for context retrieval operations."""
    
    def __init__(self, cache_impl: Cache | None = None):
        self.cache = cache_impl or LRUCache()
        self.key_prefix = "context:"
    
    def get_context(
        self,
        session_id: str,
        query: str,
        context_window: tuple[int, int],
    ) -> Any | None:
        """Get cached context for specific parameters."""
        key = self._generate_key(session_id, query, context_window)
        return self.cache.get(key)
    
    def set_context(
        self,
        session_id: str,
        query: str,
        context_window: tuple[int, int],
        context: Any,
        ttl: int | None = None,
    ) -> None:
        """Cache context for specific parameters."""
        key = self._generate_key(session_id, query, context_window)
        self.cache.set(key, context, ttl)
    
    def invalidate_session(self, session_id: str) -> None:
        """Invalidate all cache entries for a session."""
        # This is a simplified implementation
        # In practice, we'd need to track keys by session
        pass
    
    def _generate_key(
        self,
        session_id: str,
        query: str,
        context_window: tuple[int, int],
    ) -> str:
        """Generate cache key from parameters."""
        import hashlib
        
        key_data = f"{session_id}:{context_window[0]}-{context_window[1]}:{hash(query)}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{self.key_prefix}{key_hash}"


# Global cache instance
_context_cache: ContextCache | None = None


def get_context_cache() -> ContextCache:
    """Get the global context cache instance."""
    global _context_cache
    if _context_cache is None:
        _context_cache = ContextCache()
    return _context_cache
