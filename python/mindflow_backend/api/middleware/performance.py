"""Performance optimization middleware for caching and optimization."""

from __future__ import annotations

import json
import hashlib
import time
from typing import Any, Dict, Optional, Union
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for performance optimization including caching and compression."""
    
    def __init__(
        self,
        app,
        cache_ttl: int = 300,  # 5 minutes default
        max_cache_size: int = 1000,
        enable_compression: bool = True,
        compression_threshold: int = 1024
    ):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold
        
        # Simple in-memory cache (in production, use Redis or similar)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_access_times: Dict[str, float] = {}
        
        # Performance metrics
        self._request_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_response_time = 0.0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance optimizations."""
        start_time = time.time()
        self._request_count += 1
        
        # Check if request is cacheable
        cache_key = self._get_cache_key(request)
        cached_response = None
        
        if self._is_cacheable_request(request):
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                self._cache_hits += 1
                _logger.debug(f"Cache hit for {cache_key}")
                return cached_response
        
        self._cache_misses += 1
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        self._total_response_time += response_time
        
        # Add performance headers
        response = self._add_performance_headers(response, response_time)
        
        # Cache response if applicable
        if self._is_cacheable_request(request) and self._is_cacheable_response(response):
            self._store_in_cache(cache_key, response)
        
        # Apply compression if enabled and beneficial
        if self.enable_compression and self._should_compress(response):
            response = self._compress_response(response)
        
        # Log slow requests
        if response_time > 1.0:  # Log requests taking more than 1 second
            _logger.warning(
                f"Slow request detected",
                path=request.url.path,
                method=request.method,
                response_time=response_time,
                status_code=response.status_code
            )
        
        return response
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        # Include method, path, and relevant query parameters
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        
        # For POST/PUT requests, include a hash of the body
        if request.method in ["POST", "PUT", "PATCH"]:
            body_key = f"body_hash_{hash(request.url.path)}"
        else:
            body_key = ""
        
        key_string = "|".join(key_parts) + body_key
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cacheable_request(self, request: Request) -> bool:
        """Determine if request should be cached."""
        # Only cache GET requests by default
        if request.method != "GET":
            return False
        
        # Don't cache health checks or admin endpoints
        path = request.url.path
        no_cache_paths = ["/health", "/metrics", "/admin", "/debug"]
        
        return not any(path.startswith(no_cache_path) for no_cache_path in no_cache_paths)
    
    def _is_cacheable_response(self, response: Response) -> bool:
        """Determine if response should be cached."""
        # Only cache successful responses
        if response.status_code != 200:
            return False
        
        # Don't cache responses with no-cache headers
        cache_control = response.headers.get("cache-control", "")
        if "no-cache" in cache_control or "private" in cache_control:
            return False
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        cacheable_types = ["application/json", "text/html", "text/plain"]
        
        return any(content_type.startswith(ct) for ct in cacheable_types)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Response]:
        """Get response from cache if valid."""
        if cache_key not in self._cache:
            return None
        
        cached_item = self._cache[cache_key]
        current_time = time.time()
        
        # Check if cache entry is expired
        if current_time - cached_item["timestamp"] > self.cache_ttl:
            del self._cache[cache_key]
            if cache_key in self._cache_access_times:
                del self._cache_access_times[cache_key]
            return None
        
        # Update access time for LRU
        self._cache_access_times[cache_key] = current_time
        
        # Recreate response — exclude content-length so JSONResponse calculates it correctly
        headers = {
            k: v for k, v in cached_item["headers"].items()
            if k.lower() not in ("content-length",)
        }
        return JSONResponse(
            content=cached_item["content"],
            status_code=cached_item["status_code"],
            headers=headers,
        )
    
    def _store_in_cache(self, cache_key: str, response: Response) -> None:
        """Store response in cache."""
        # Implement LRU eviction if cache is full
        if len(self._cache) >= self.max_cache_size:
            self._evict_lru()
        
        # Store response data
        try:
            content = response.body.decode() if hasattr(response, 'body') else ""
        except (UnicodeDecodeError, AttributeError):
            content = ""
        
        self._cache[cache_key] = {
            "content": json.loads(content) if content else {},
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "timestamp": time.time()
        }
        
        self._cache_access_times[cache_key] = time.time()
    
    def _evict_lru(self) -> None:
        """Evict least recently used cache entry."""
        if not self._cache_access_times:
            return
        
        # Find the least recently used key
        lru_key = min(self._cache_access_times.keys(), 
                      key=lambda k: self._cache_access_times[k])
        
        # Remove from cache
        del self._cache[lru_key]
        del self._cache_access_times[lru_key]
        
        _logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def _should_compress(self, response: Response) -> bool:
        """Determine if response should be compressed."""
        # Only compress if response is large enough
        try:
            content_length = len(response.body) if hasattr(response, 'body') else 0
        except (AttributeError, TypeError):
            content_length = 0
        
        return content_length >= self.compression_threshold
    
    def _compress_response(self, response: Response) -> Response:
        """Apply compression to response (placeholder — no-op until real gzip is wired)."""
        # NOTE: Do NOT set content-encoding without actually compressing the body.
        _logger.debug("Compression skipped (not yet implemented)")
        return response
    
    def _add_performance_headers(self, response: Response, response_time: float) -> Response:
        """Add performance-related headers to response."""
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"
        response.headers["X-Cache-Status"] = "hit" if self._cache_hits > self._cache_misses else "miss"
        response.headers["X-Request-Count"] = str(self._request_count)
        
        # Add cache control headers for cacheable responses
        if self._is_cacheable_response(response):
            response.headers["Cache-Control"] = f"public, max-age={self.cache_ttl}"
        
        return response
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        avg_response_time = (self._total_response_time / self._request_count) if self._request_count > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._cache),
            "max_cache_size": self.max_cache_size,
            "total_requests": self._request_count,
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "cache_ttl_seconds": self.cache_ttl
        }
    
    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._cache_access_times.clear()
        _logger.info("Cache cleared")


class DatabaseConnectionPoolMiddleware(BaseHTTPMiddleware):
    """Middleware for optimizing database connection usage."""
    
    def __init__(self, app, max_connections: int = 20):
        super().__init__(app)
        self.max_connections = max_connections
        self._active_connections = 0
        self._connection_stats = {
            "total_requests": 0,
            "connection_errors": 0,
            "avg_connection_time": 0.0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Optimize database connection usage."""
        start_time = time.time()
        self._connection_stats["total_requests"] += 1
        
        try:
            # Check connection pool availability
            if self._active_connections >= self.max_connections:
                _logger.warning("Database connection pool exhausted")
                # Could implement queuing or return 503
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Service temporarily unavailable"}
                )
            
            self._active_connections += 1
            
            # Process request
            response = await call_next(request)
            
            # Update connection stats
            connection_time = time.time() - start_time
            total_time = self._connection_stats["avg_connection_time"] * (self._connection_stats["total_requests"] - 1)
            self._connection_stats["avg_connection_time"] = (total_time + connection_time) / self._connection_stats["total_requests"]
            
            return response
            
        except Exception as e:
            self._connection_stats["connection_errors"] += 1
            _logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            self._active_connections -= 1
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get database connection statistics."""
        return {
            "active_connections": self._active_connections,
            "max_connections": self.max_connections,
            "total_requests": self._connection_stats["total_requests"],
            "connection_errors": self._connection_stats["connection_errors"],
            "avg_connection_time_ms": round(self._connection_stats["avg_connection_time"] * 1000, 2),
            "error_rate_percent": round(
                (self._connection_stats["connection_errors"] / self._connection_stats["total_requests"] * 100)
                if self._connection_stats["total_requests"] > 0 else 0, 2
            )
        }
