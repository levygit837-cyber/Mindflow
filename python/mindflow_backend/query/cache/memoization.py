"""Memoization utilities for expensive operations.

Provides caching decorators for expensive operations:
- Git status, branch info, remote info
- File discovery (glob, find, list_dir)
- System information queries

Inspired by Claude Code's memoization patterns:
- `memoize()` for expensive git operations
- TTL-based cache invalidation
- Automatic cache clearing on git mutations

Usage:
    from mindflow_backend.query.cache.memoization import memoize_git, memoize_file_discovery
    
    @memoize_git(ttl=30)
    async def get_git_status(root_dir: str) -> dict:
        # Expensive git operation
        ...
    
    @memoize_file_discovery(ttl=60)
    async def discover_files(pattern: str) -> list[str]:
        # Expensive file discovery
        ...
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Global cache registry for clearing
_git_caches: list[dict[str, Any]] = []
_file_caches: list[dict[str, Any]] = []


class MemoizedResult:
    """A memoized result with TTL support."""

    def __init__(self, value: Any, ttl: int) -> None:
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_valid(self) -> bool:
        """Check if the cached result is still valid."""
        return (time.time() - self.created_at) < self.ttl

    def age_seconds(self) -> float:
        """Get the age of the cached result in seconds."""
        return time.time() - self.created_at


def _make_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """Create a cache key from function name and arguments."""
    key_parts = [func.__module__, func.__qualname__]

    # Add positional args
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        elif hasattr(arg, "__fspath__"):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(id(arg)))

    # Add keyword args (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()[:16]


def memoize_git(ttl: int = 30) -> Callable[[F], F]:
    """Memoize git operations with TTL-based invalidation.

    Args:
        ttl: Time-to-live in seconds (default: 30).

    Returns:
        Decorator function.

    Example:
        @memoize_git(ttl=30)
        async def get_git_status(root_dir: str) -> dict:
            # Expensive git status operation
            ...
    """
    cache: dict[str, MemoizedResult] = {}
    _git_caches.append(cache)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = _make_cache_key(func, args, kwargs)

            # Check cache
            if cache_key in cache:
                cached = cache[cache_key]
                if cached.is_valid():
                    logger.debug(
                        "memoize_git_hit",
                        func=func.__name__,
                        age=f"{cached.age_seconds():.1f}s",
                    )
                    return cached.value
                else:
                    # Expired
                    del cache[cache_key]

            # Cache miss — execute function
            result = await func(*args, **kwargs)
            cache[cache_key] = MemoizedResult(result, ttl)

            logger.debug(
                "memoize_git_miss",
                func=func.__name__,
                ttl=ttl,
            )
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = _make_cache_key(func, args, kwargs)

            # Check cache
            if cache_key in cache:
                cached = cache[cache_key]
                if cached.is_valid():
                    logger.debug(
                        "memoize_git_hit",
                        func=func.__name__,
                        age=f"{cached.age_seconds():.1f}s",
                    )
                    return cached.value
                else:
                    del cache[cache_key]

            # Cache miss — execute function
            result = func(*args, **kwargs)
            cache[cache_key] = MemoizedResult(result, ttl)

            logger.debug(
                "memoize_git_miss",
                func=func.__name__,
                ttl=ttl,
            )
            return result

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def memoize_file_discovery(ttl: int = 60) -> Callable[[F], F]:
    """Memoize file discovery operations with TTL-based invalidation.

    Args:
        ttl: Time-to-live in seconds (default: 60).

    Returns:
        Decorator function.

    Example:
        @memoize_file_discovery(ttl=60)
        async def discover_files(pattern: str, root_dir: str) -> list[str]:
            # Expensive file discovery
            ...
    """
    cache: dict[str, MemoizedResult] = {}
    _file_caches.append(cache)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = _make_cache_key(func, args, kwargs)

            # Check cache
            if cache_key in cache:
                cached = cache[cache_key]
                if cached.is_valid():
                    logger.debug(
                        "memoize_file_discovery_hit",
                        func=func.__name__,
                        age=f"{cached.age_seconds():.1f}s",
                    )
                    return cached.value
                else:
                    del cache[cache_key]

            # Cache miss — execute function
            result = await func(*args, **kwargs)
            cache[cache_key] = MemoizedResult(result, ttl)

            logger.debug(
                "memoize_file_discovery_miss",
                func=func.__name__,
                ttl=ttl,
            )
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = _make_cache_key(func, args, kwargs)

            # Check cache
            if cache_key in cache:
                cached = cache[cache_key]
                if cached.is_valid():
                    logger.debug(
                        "memoize_file_discovery_hit",
                        func=func.__name__,
                        age=f"{cached.age_seconds():.1f}s",
                    )
                    return cached.value
                else:
                    del cache[cache_key]

            # Cache miss — execute function
            result = func(*args, **kwargs)
            cache[cache_key] = MemoizedResult(result, ttl)

            logger.debug(
                "memoize_file_discovery_miss",
                func=func.__name__,
                ttl=ttl,
            )
            return result

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def clear_all_git_caches() -> int:
    """Clear all git memoization caches.

    Call this after git mutations (commit, checkout, merge, etc.)

    Returns:
        Number of cache entries cleared.
    """
    total = 0
    for cache in _git_caches:
        total += len(cache)
        cache.clear()

    logger.info("memoize_git_caches_cleared", entries=total)
    return total


def clear_all_file_caches() -> int:
    """Clear all file discovery memoization caches.

    Call this after file system mutations.

    Returns:
        Number of cache entries cleared.
    """
    total = 0
    for cache in _file_caches:
        total += len(cache)
        cache.clear()

    logger.info("memoize_file_caches_cleared", entries=total)
    return total


def clear_all_caches() -> dict[str, int]:
    """Clear all memoization caches.

    Returns:
        Dictionary with counts of cleared entries per type.
    """
    git_cleared = clear_all_git_caches()
    file_cleared = clear_all_file_caches()

    return {
        "git": git_cleared,
        "file": file_cleared,
        "total": git_cleared + file_cleared,
    }


def get_memoization_stats() -> dict[str, Any]:
    """Get statistics about all memoization caches.

    Returns:
        Dictionary with cache statistics.
    """
    git_entries = sum(len(c) for c in _git_caches)
    file_entries = sum(len(c) for c in _file_caches)

    git_valid = sum(
        1 for c in _git_caches for v in c.values() if v.is_valid()
    )
    file_valid = sum(
        1 for c in _file_caches for v in c.values() if v.is_valid()
    )

    return {
        "git": {
            "total_entries": git_entries,
            "valid_entries": git_valid,
            "expired_entries": git_entries - git_valid,
            "cache_count": len(_git_caches),
        },
        "file": {
            "total_entries": file_entries,
            "valid_entries": file_valid,
            "expired_entries": file_entries - file_valid,
            "cache_count": len(_file_caches),
        },
        "total": {
            "entries": git_entries + file_entries,
            "valid": git_valid + file_valid,
        },
    }