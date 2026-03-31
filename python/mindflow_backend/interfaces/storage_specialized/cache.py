"""Cache storage interfaces.

Extends core cache interface with storage-specific contracts
and management operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...schemas.storage_specialized.cache import (
    CacheHealthCheck,
    CacheStats,
)


class CacheManagerInterface(ABC):
    """High-level cache management interface."""
    
    @abstractmethod
    async def get_cache_info(self) -> dict[str, Any]:
        """Get cache information."""
        pass
    
    @abstractmethod
    async def get_performance_metrics(self) -> CacheStats:
        """Get performance metrics."""
        pass
    
    @abstractmethod
    async def health_check(self) -> CacheHealthCheck:
        """Perform health check."""
        pass
    
    @abstractmethod
    async def clear_all(self) -> bool:
        """Clear all cache data."""
        pass
    
    @abstractmethod
    async def get_size_info(self) -> dict[str, Any]:
        """Get size information."""
        pass


class CacheDistributedInterface(ABC):
    """Interface for distributed cache operations."""
    
    @abstractmethod
    async def get_nodes(self) -> list[dict[str, Any]]:
        """Get cache cluster nodes."""
        pass
    
    @abstractmethod
    async def add_node(self, node_config: dict[str, Any]) -> bool:
        """Add cache node."""
        pass
    
    @abstractmethod
    async def remove_node(self, node_id: str) -> bool:
        """Remove cache node."""
        pass
    
    @abstractmethod
    async def replicate_data(
        self,
        key: str,
        value: Any,
        target_nodes: list[str] | None = None
    ) -> dict[str, Any]:
        """Replicate data to nodes."""
        pass
    
    @abstractmethod
    async def get_cluster_stats(self) -> dict[str, Any]:
        """Get cluster statistics."""
        pass


class CachePersistenceInterface(ABC):
    """Interface for cache persistence operations."""
    
    @abstractmethod
    async def save_to_disk(self, file_path: str) -> dict[str, Any]:
        """Save cache to disk."""
        pass
    
    @abstractmethod
    async def load_from_disk(self, file_path: str) -> dict[str, Any]:
        """Load cache from disk."""
        pass
    
    @abstractmethod
    async def auto_save(self, enabled: bool, interval: int = 300) -> None:
        """Configure auto-save."""
        pass
    
    @abstractmethod
    async def get_persistence_info(self) -> dict[str, Any]:
        """Get persistence information."""
        pass


class CacheWarmerInterface(ABC):
    """Interface for cache warming operations."""
    
    @abstractmethod
    async def warm_cache(self, keys: list[str], values: list[Any]) -> dict[str, Any]:
        """Warm cache with data."""
        pass
    
    @abstractmethod
    async def warm_by_pattern(self, pattern: str, limit: int = 1000) -> dict[str, Any]:
        """Warm cache by key pattern."""
        pass
    
    @abstractmethod
    async def warm_from_data_source(self, query: str) -> dict[str, Any]:
        """Warm cache from data source."""
        pass
    
    @abstractmethod
    async def get_warming_stats(self) -> dict[str, Any]:
        """Get warming statistics."""
        pass


class CacheInvalidationInterface(ABC):
    """Interface for cache invalidation strategies."""
    
    @abstractmethod
    async def invalidate_by_key(self, key: str) -> bool:
        """Invalidate by key."""
        pass
    
    @abstractmethod
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate by pattern."""
        pass
    
    @abstractmethod
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate by tag."""
        pass
    
    @abstractmethod
    async def invalidate_by_ttl(self) -> int:
        """Invalidate expired entries."""
        pass
    
    @abstractmethod
    async def set_invalidation_callback(
        self,
        callback_func: callable,
        event_types: list[str]
    ) -> None:
        """Set invalidation callback."""
        pass
