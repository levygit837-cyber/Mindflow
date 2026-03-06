from functools import lru_cache

import redis
import redis.asyncio as redis_async

from .config import get_settings


@lru_cache(maxsize=1)
def get_sync_redis() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache(maxsize=1)
def get_async_redis() -> redis_async.Redis:
    settings = get_settings()
    return redis_async.from_url(settings.redis_url, decode_responses=True)
