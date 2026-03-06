"""Advanced caching middleware with Redis support."""

from __future__ import annotations

import json
import pickle
import hashlib
import time
from typing import Any, Dict, Optional, Union, Callable
from collections.abc import AsyncGenerator

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CacheBackend:
    """Abstract cache backend interface."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL."""
        raise NotImplementedError
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        raise NotImplementedError
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend for development/testing."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        current_time = time.time()
        
        # Check expiration
        if current_time > entry["expires_at"]:
            await self.delete(key)
            return None
        
        # Update access time for LRU
        self._access_times[key] = current_time
        return entry["value"]
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in memory cache."""
        # Implement LRU eviction if needed
        if len(self._cache) >= self.max_size:
            await self._evict_lru()
        
        current_time = time.time()
        self._cache[key] = {
            "value": value,
            "created_at": current_time,
            "expires_at": current_time + ttl
        }
        self._access_times[key] = current_time
    
    async def delete(self, key: str) -> None:
        """Delete key from memory cache."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
    
    async def clear(self) -> None:
        """Clear memory cache."""
        self._cache.clear()
        self._access_times.clear()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        return key in self._cache
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        await self.delete(lru_key)


class RedisCacheBackend(CacheBackend):
    """Redis cache backend for production."""
    
    def __init__(self, redis_url: str, key_prefix: str = "mindflow:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis_client = None
    
    async def _get_client(self):
        """Get Redis client (lazy initialization)."""
        if self._redis_client is None:
            try:
                import aioredis
                self._redis_client = await aioredis.from_url(self.redis_url)
            except ImportError:
                _logger.error("aioredis not installed, falling back to memory cache")
                return None
        return self._redis_client
    
    def _make_key(self, key: str) -> str:
        """Add prefix to cache key."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        client = await self._get_client()
        if not client:
            return None
        
        try:
            value = await client.get(self._make_key(key))
            if value is None:
                return None
            
            return pickle.loads(value)
        except Exception as e:
            _logger.error(f"Redis get error: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in Redis cache."""
        client = await self._get_client()
        if not client:
            return
        
        try:
            serialized_value = pickle.dumps(value)
            await client.setex(self._make_key(key), ttl, serialized_value)
        except Exception as e:
            _logger.error(f"Redis set error: {str(e)}")
    
    async def delete(self, key: str) -> None:
        """Delete key from Redis cache."""
        client = await self._get_client()
        if not client:
            return
        
        try:
            await client.delete(self._make_key(key))
        except Exception as e:
            _logger.error(f"Redis delete error: {str(e)}")
    
    async def clear(self) -> None:
        """Clear all cache entries with prefix."""
        client = await self._get_client()
        if not client:
            return
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
        except Exception as e:
            _logger.error(f"Redis clear error: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        client = await self._get_client()
        if not client:
            return False
        
        try:
            return bool(await client.exists(self._make_key(key)))
        except Exception as e:
            _logger.error(f"Redis exists error: {str(e)}")
            return False


class AdvancedCacheMiddleware(BaseHTTPMiddleware):
    """Advanced caching middleware with multiple backends and strategies."""
    
    def __init__(
        self,
        app,
        cache_backend: Optional[CacheBackend] = None,
        default_ttl: int = 300,  # 5 minutes
        strategies: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        super().__init__(app)
        self.cache_backend = cache_backend or MemoryCacheBackend()
        self.default_ttl = default_ttl
        
        # Caching strategies per endpoint
        self.strategies = strategies or {
            # Agent endpoints
            "/v1/agent/capabilities": {"ttl": 600, "vary": ["agent_type"]},
            "/v1/agent/list": {"ttl": 300, "vary": []},
            
            # Provider endpoints
            "/v1/providers/": {"ttl": 1800, "vary": []},  # 30 minutes
            "/v1/providers/{provider_id}/models": {"ttl": 3600, "vary": ["provider_id"]},
            
            # Session endpoints (shorter TTL for user data)
            "/v1/chat/sessions": {"ttl": 60, "vary": ["limit", "offset"]},
            
            # Orchestration endpoints (don't cache by default)
            "/v1/orchestration/": {"ttl": 0, "vary": []},
        }
        
        # Statistics
        self._stats = {
            "requests": 0,
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with advanced caching."""
        self._stats["requests"] += 1
        
        # Determine caching strategy
        strategy = self._get_strategy(request)
        
        # Skip caching if disabled
        if strategy.get("ttl", 0) == 0:
            return await call_next(request)
        
        # Generate cache key
        cache_key = await self._generate_cache_key(request, strategy)
        
        # Try to get from cache
        cached_response = await self._get_cached_response(cache_key)
        if cached_response:
            self._stats["hits"] += 1
            return cached_response
        
        self._stats["misses"] += 1
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            self._stats["errors"] += 1
            raise
        
        # Cache response if appropriate
        if await self._should_cache_response(request, response, strategy):
            await self._cache_response(cache_key, response, strategy)
        
        return response
    
    def _get_strategy(self, request: Request) -> Dict[str, Any]:
        """Get caching strategy for request."""
        path = request.url.path
        
        # Find matching strategy
        for pattern, strategy in self.strategies.items():
            if self._path_matches(path, pattern):
                return strategy.copy()
        
        # Default strategy
        return {"ttl": self.default_ttl, "vary": []}
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern (supports simple wildcards)."""
        if pattern == path:
            return True
        
        # Handle path parameters like {provider_id}
        if "{" in pattern:
            pattern_parts = pattern.split("/")
            path_parts = path.split("/")
            
            if len(pattern_parts) != len(path_parts):
                return False
            
            for pattern_part, path_part in zip(pattern_parts, path_parts):
                if pattern_part.startswith("{") and pattern_part.endswith("}"):
                    continue  # Parameter matches anything
                elif pattern_part != path_part:
                    return False
            
            return True
        
        return False
    
    async def _generate_cache_key(self, request: Request, strategy: Dict[str, Any]) -> str:
        """Generate cache key based on request and strategy."""
        key_parts = [
            request.method,
            request.url.path
        ]
        
        # Add varying parameters
        for param in strategy.get("vary", []):
            if param in request.query_params:
                key_parts.append(f"{param}={request.query_params[param]}")
        
        # Add path parameters for patterns
        path_pattern = next(
            (pattern for pattern in self.strategies.keys() 
             if self._path_matches(request.url.path, pattern)),
            None
        )
        
        if path_pattern and "{" in path_pattern:
            # Extract path parameters
            pattern_parts = path_pattern.split("/")
            path_parts = request.url.path.split("/")
            
            for i, (pattern_part, path_part) in enumerate(zip(pattern_parts, path_parts)):
                if pattern_part.startswith("{") and pattern_part.endswith("}"):
                    param_name = pattern_part[1:-1]
                    key_parts.append(f"{param_name}={path_part}")
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Response]:
        """Get response from cache."""
        try:
            cached_data = await self.cache_backend.get(cache_key)
            if cached_data is None:
                return None
            
            return JSONResponse(
                content=cached_data["content"],
                status_code=cached_data["status_code"],
                headers=cached_data["headers"]
            )
        except Exception as e:
            _logger.error(f"Cache get error: {str(e)}")
            return None
    
    async def _should_cache_response(self, request: Request, response: Response, strategy: Dict[str, Any]) -> bool:
        """Determine if response should be cached."""
        # Only cache successful responses
        if response.status_code != 200:
            return False
        
        # Don't cache if response has no-cache headers
        cache_control = response.headers.get("cache-control", "")
        if "no-cache" in cache_control or "private" in cache_control:
            return False
        
        # Check content length (don't cache very large responses)
        try:
            content_length = len(response.body) if hasattr(response, 'body') else 0
            if content_length > 1024 * 1024:  # 1MB limit
                return False
        except (AttributeError, TypeError):
            pass
        
        return True
    
    async def _cache_response(self, cache_key: str, response: Response, strategy: Dict[str, Any]) -> None:
        """Cache response."""
        try:
            # Extract response data
            content = response.body.decode() if hasattr(response, 'body') else "{}"
            
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                parsed_content = {}
            
            cached_data = {
                "content": parsed_content,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "cached_at": time.time()
            }
            
            await self.cache_backend.set(cache_key, cached_data, strategy["ttl"])
            self._stats["sets"] += 1
            
        except Exception as e:
            _logger.error(f"Cache set error: {str(e)}")
    
    async def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        # This is a simplified implementation
        # In production, you'd use Redis patterns or maintain an index
        try:
            await self.cache_backend.clear()
            self._stats["deletes"] += 1
            return 1
        except Exception as e:
            _logger.error(f"Cache invalidation error: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "requests": self._stats["requests"],
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "errors": self._stats["errors"],
            "hit_rate_percent": round(hit_rate, 2),
            "backend_type": type(self.cache_backend).__name__
        }
    
    async def clear_stats(self) -> None:
        """Clear cache statistics."""
        for key in self._stats:
            self._stats[key] = 0


class CacheWarmer:
    """Utility for warming up cache with common requests."""
    
    def __init__(self, cache_backend: CacheBackend):
        self.cache_backend = cache_backend
    
    async def warm_agent_cache(self) -> None:
        """Warm up agent-related cache entries."""
        # Pre-cache common agent capabilities
        agent_types = ["analyst", "coder", "researcher", "reviewer"]
        
        for agent_type in agent_types:
            cache_key = f"agent_capabilities:{agent_type}"
            capabilities = {
                "agent_type": agent_type,
                "capabilities": ["analysis", "coding"],
                "status": "active"
            }
            await self.cache_backend.set(cache_key, capabilities, 600)  # 10 minutes
    
    async def warm_provider_cache(self) -> None:
        """Warm up provider-related cache entries."""
        providers = [
            {"id": "google", "name": "Google/VertexAI", "status": "active"},
            {"id": "anthropic", "name": "Anthropic", "status": "active"},
            {"id": "openai", "name": "OpenAI", "status": "active"}
        ]
        
        cache_key = "providers_list"
        await self.cache_backend.set(cache_key, providers, 1800)  # 30 minutes
