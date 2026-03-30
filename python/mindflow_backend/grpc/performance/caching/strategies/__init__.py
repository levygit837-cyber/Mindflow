"""Cache eviction strategies.

Provides specialized caching strategies optimized for
different access patterns, content types, and performance requirements.
"""

from .base import CacheStrategy
from .lru import LRUCacheStrategy
from .ttl import TTLCacheStrategy
from .size_based import SizeBasedCacheStrategy

__all__ = [
    "CacheStrategy",
    "LRUCacheStrategy",
    "TTLCacheStrategy",
    "SizeBasedCacheStrategy",
]