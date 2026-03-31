"""Vector storage interfaces.

Extends core vector interface with storage-specific contracts
and high-level operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...schemas.storage_specialized.vector import (
    VectorBatchRequest,
    VectorBatchResponse,
    VectorCollection,
    VectorConfig,
    VectorSearchRequest,
    VectorSearchResponse,
)


class VectorStoreInterface(ABC):
    """High-level vector store interface."""
    
    @abstractmethod
    async def get_collections(self) -> list[VectorCollection]:
        """Get all collections."""
        pass
    
    @abstractmethod
    async def create_collection_with_config(self, config: VectorConfig) -> VectorCollection:
        """Create collection with configuration."""
        pass
    
    @abstractmethod
    async def drop_collection(self, collection_name: str) -> bool:
        """Drop collection."""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics."""
        pass
    
    @abstractmethod
    async def optimize_collection(self, collection_name: str) -> dict[str, Any]:
        """Optimize collection index."""
        pass


class VectorManagerInterface(ABC):
    """Interface for vector database management."""
    
    @abstractmethod
    async def get_database_info(self) -> dict[str, Any]:
        """Get database information."""
        pass
    
    @abstractmethod
    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        pass
    
    @abstractmethod
    async def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        pass
    
    @abstractmethod
    async def backup_database(self, backup_path: str) -> dict[str, Any]:
        """Backup database."""
        pass
    
    @abstractmethod
    async def restore_database(self, backup_path: str) -> dict[str, Any]:
        """Restore database."""
        pass
    
    @abstractmethod
    async def compact_database(self) -> dict[str, Any]:
        """Compact database."""
        pass
    
    @abstractmethod
    async def reindex_collection(self, collection_name: str) -> dict[str, Any]:
        """Reindex collection."""
        pass


class VectorIndexInterface(ABC):
    """Interface for vector indexing operations."""
    
    @abstractmethod
    async def create_index(self, collection_name: str, index_config: dict[str, Any]) -> bool:
        """Create index."""
        pass
    
    @abstractmethod
    async def drop_index(self, collection_name: str, index_name: str) -> bool:
        """Drop index."""
        pass
    
    @abstractmethod
    async def list_indexes(self, collection_name: str) -> list[dict[str, Any]]:
        """List indexes."""
        pass
    
    @abstractmethod
    async def get_index_stats(self, collection_name: str, index_name: str) -> dict[str, Any]:
        """Get index statistics."""
        pass
    
    @abstractmethod
    async def optimize_index(self, collection_name: str, index_name: str) -> dict[str, Any]:
        """Optimize index."""
        pass


class VectorMigrationInterface(ABC):
    """Interface for vector database migrations."""
    
    @abstractmethod
    async def migrate_collection(
        self,
        source_collection: str,
        target_collection: str,
        config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Migrate collection data."""
        pass
    
    @abstractmethod
    async def migrate_database(
        self,
        source_config: VectorConfig,
        target_config: VectorConfig,
        options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Migrate entire database."""
        pass
    
    @abstractmethod
    async def validate_migration(self, migration_id: str) -> dict[str, Any]:
        """Validate migration integrity."""
        pass


class VectorCacheInterface(ABC):
    """Interface for vector caching operations."""
    
    @abstractmethod
    async def cache_search_result(
        self,
        query_hash: str,
        results: list[dict[str, Any]],
        ttl: int = 3600
    ) -> bool:
        """Cache search results."""
        pass
    
    @abstractmethod
    async def get_cached_search(self, query_hash: str) -> list[dict[str, Any]] | None:
        """Get cached search results."""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, collection_name: str, vector_ids: list[str]) -> None:
        """Invalidate cache entries."""
        pass
    
    @abstractmethod
    async def clear_cache(self, collection_name: str | None = None) -> None:
        """Clear cache."""
        pass


class VectorBatchInterface(ABC):
    """Interface for batch vector operations."""
    
    @abstractmethod
    async def batch_insert(
        self,
        collection_name: str,
        batch_request: VectorBatchRequest
    ) -> VectorBatchResponse:
        """Batch insert vectors."""
        pass
    
    @abstractmethod
    async def batch_update(
        self,
        collection_name: str,
        updates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Batch update vectors."""
        pass
    
    @abstractmethod
    async def batch_delete(
        self,
        collection_name: str,
        vector_ids: list[str]
    ) -> dict[str, Any]:
        """Batch delete vectors."""
        pass
    
    @abstractmethod
    async def batch_search(
        self,
        collection_name: str,
        queries: list[VectorSearchRequest]
    ) -> list[VectorSearchResponse]:
        """Batch search vectors."""
        pass
