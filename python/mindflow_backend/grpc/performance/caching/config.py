"""Configuration for gRPC response caching.

Defines cache configuration and eviction policies.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    cacheable_content_types: list[str] = field(default_factory=lambda: [
        "application/json",
        "application/x-protobuf",
        "text/plain",
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

    def generate_cache_key(
        self,
        method: str,
        request_data: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> str:
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