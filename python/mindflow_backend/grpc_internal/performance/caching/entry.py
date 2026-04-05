"""Cache entry data model.

Defines the cache entry structure with metadata.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """Cache entry with metadata.

    Attributes:
        key: Cache key
        value: Cached value (bytes)
        created_at: Creation timestamp
        last_accessed: Last access timestamp
        access_count: Number of accesses
        ttl_seconds: Time to live in seconds
        size_bytes: Size in bytes
        metadata: Optional metadata
    """

    key: str
    value: bytes
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl_seconds: float | None = None
    size_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = len(self.value)

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at

    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = time.time()
        self.access_count += 1