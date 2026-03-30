from functools import lru_cache

from rq import Queue

from mindflow_backend.infra.cache.redis_client import get_sync_redis


@lru_cache(maxsize=1)
def get_queue() -> Queue:
    return Queue("default", connection=get_sync_redis())
