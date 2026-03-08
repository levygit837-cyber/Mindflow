"""Cache implementation for personality selection.

Provides caching for personality decisions to improve
performance and consistency across sessions.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional
from collections import OrderedDict

from mindflow_backend.agents.core.interfaces import Cache
from mindflow_backend.agents.core.exceptions import CacheError
from mindflow_backend.config.agents import get_agent_config


class PersonalityCache:
    """Specialized cache for personality selection operations."""
    
    def __init__(self, cache_impl: Cache | None = None):
        self.cache = cache_impl or LRUPersonalityCache()
        self.key_prefix = "personality:"
    
    def get_decision(
        self,
        task_signature: str,
    ) -> Any | None:
        """Get cached personality decision for task signature."""
        key = self._generate_key(task_signature)
        return self.cache.get(key)
    
    def set_decision(
        self,
        task_signature: str,
        decision: Any,
        ttl: int | None = None,
    ) -> None:
        """Cache personality decision for task signature."""
        key = self._generate_key(task_signature)
        self.cache.set(key, decision, ttl)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get personality cache statistics."""
        if hasattr(self.cache, 'get_stats'):
            return self.cache.get_stats()
        return {"cache_type": type(self.cache).__name__}
    
    def _generate_key(self, task_signature: str) -> str:
        """Generate cache key from task signature."""
        return f"{self.key_prefix}{task_signature}"


class LRUPersonalityCache(Cache):
    """Thread-safe LRU cache for personality decisions."""
    
    def __init__(self, max_size: int | None = None, default_ttl: int | None = None):
        self.max_size = max_size or get_agent_config().personality_cache_size
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
            
            # Update usage count
            entry["usage_count"] += 1
            entry["last_accessed"] = time.time()
            
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
                    "usage_count": 1,
                    "last_accessed": time.time(),
                }
                
                # Move to end
                self._cache.move_to_end(key)
        
        except Exception as e:
            raise CacheError(f"Failed to set cache entry: {e}", operation="set", key=key)
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
        except Exception as e:
            raise CacheError(f"Failed to delete cache entry: {e}", operation="delete", key=key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            with self._lock:
                self._cache.clear()
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {e}", operation="clear")
    
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
            
            total_usage = sum(
                entry.get("usage_count", 0) 
                for entry in self._cache.values()
            )
            
            # Calculate tokens saved (estimate)
            tokens_saved = sum(
                entry.get("value", {}).get("estimated_tokens_saved", 0)
                for entry in self._cache.values()
                if isinstance(entry.get("value"), dict)
            )
            
            return {
                "total_entries": total_entries,
                "max_size": self.max_size,
                "expired_entries": expired_entries,
                "usage_ratio": total_entries / self.max_size if self.max_size > 0 else 0,
                "total_usage": total_usage,
                "total_tokens_saved": tokens_saved,
                "average_success_rate": self._calculate_average_success_rate(),
            }
    
    def _calculate_average_success_rate(self) -> float:
        """Calculate average success rate of cached decisions."""
        success_rates = [
            entry.get("value", {}).get("success_rate", 0.0)
            for entry in self._cache.values()
            if isinstance(entry.get("value"), dict)
        ]
        
        if not success_rates:
            return 0.0
        
        return sum(success_rates) / len(success_rates)


# Global cache instance
_personality_cache: PersonalityCache | None = None


def get_personality_cache() -> PersonalityCache:
    """Get the global personality cache instance."""
    global _personality_cache
    if _personality_cache is None:
        _personality_cache = PersonalityCache()
    return _personality_cache
