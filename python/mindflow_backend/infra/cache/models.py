"""Cache data models and enums.

Provides cache levels, policies, and entry dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, Optional


class CacheLevel(Enum):
    """Cache levels in the hierarchy."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"


class CachePolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheEntry:
    """Cache entry with metadata.

    Attributes:
        value: Cached value
        created_at: Creation timestamp
        last_accessed: Last access timestamp
        access_count: Number of accesses
        ttl: Time to live in seconds
        size_bytes: Estimated size in bytes
        tags: Optional tags for invalidation
    """
    value: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    tags: Dict[str, str] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return (datetime.now(UTC) - self.created_at).total_seconds() > self.ttl

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return (datetime.now(UTC) - self.created_at).total_seconds()

    def touch(self) -> None:
        """Update last access time and count."""
        self.last_accessed = datetime.now(UTC)
        self.access_count += 1