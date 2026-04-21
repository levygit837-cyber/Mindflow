"""Advanced cache infrastructure for MindFlow backend.

Expose cache helpers lazily so callers can import a specific cache primitive
without forcing Redis/playwright-related optional dependencies during test
collection.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "CacheBackend",
    "CacheEntry",
    "CacheInvalidator",
    "CacheLevel",
    "CacheManager",
    "CachePolicy",
    "CacheWarmer",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "RedisClient",
    "get_async_redis",
    "get_cache_invalidator",
    "get_cache_manager",
    "get_cache_warmer",
    "get_redis_client",
    "get_sync_redis",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "CacheBackend": ("mindflow_backend.infra.cache.backends", "CacheBackend"),
    "MemoryCacheBackend": ("mindflow_backend.infra.cache.backends", "MemoryCacheBackend"),
    "RedisCacheBackend": ("mindflow_backend.infra.cache.backends", "RedisCacheBackend"),
    "CacheManager": ("mindflow_backend.infra.cache.cache_manager", "CacheManager"),
    "get_cache_manager": ("mindflow_backend.infra.cache.cache_manager", "get_cache_manager"),
    "CacheInvalidator": (
        "mindflow_backend.infra.cache.invalidation",
        "CacheInvalidator",
    ),
    "get_cache_invalidator": (
        "mindflow_backend.infra.cache.invalidation",
        "get_cache_invalidator",
    ),
    "CacheEntry": ("mindflow_backend.infra.cache.models", "CacheEntry"),
    "CacheLevel": ("mindflow_backend.infra.cache.models", "CacheLevel"),
    "CachePolicy": ("mindflow_backend.infra.cache.models", "CachePolicy"),
    "RedisClient": ("mindflow_backend.infra.cache.redis_client", "RedisClient"),
    "get_async_redis": ("mindflow_backend.infra.cache.redis_client", "get_async_redis"),
    "get_redis_client": ("mindflow_backend.infra.cache.redis_client", "get_redis_client"),
    "get_sync_redis": ("mindflow_backend.infra.cache.redis_client", "get_sync_redis"),
    "CacheWarmer": ("mindflow_backend.infra.cache.warming", "CacheWarmer"),
    "get_cache_warmer": ("mindflow_backend.infra.cache.warming", "get_cache_warmer"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _LAZY_ATTRS[name]
    except KeyError as exc:  # pragma: no cover - Python fallback path
        raise AttributeError(name) from exc
    module = import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
