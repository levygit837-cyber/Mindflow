"""Storage-specific schemas.

Integrates with global schema system while providing storage-specific
contracts and data structures.
"""

from .database import (
    DatabaseConfig,
    ConnectionConfig,
    PoolConfig,
    HealthCheckConfig,
    MigrationConfig,
)

from .vector import (
    VectorConfig,
    VectorCollection,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorMetadata,
)

from .cache import (
    CacheConfig,
    CacheEntry,
    CacheStats,
)

from .memory import (
    StorageMemoryEntry,
    StorageMemoryWindow,
    StorageMemoryStats,
)

__all__ = [
    # Database schemas
    "DatabaseConfig",
    "ConnectionConfig", 
    "PoolConfig",
    "HealthCheckConfig",
    "MigrationConfig",
    # Vector schemas
    "VectorConfig",
    "VectorCollection",
    "VectorSearchRequest",
    "VectorSearchResponse",
    "VectorMetadata",
    # Cache schemas
    "CacheConfig",
    "CacheEntry",
    "CacheStats",
    # Memory schemas
    "StorageMemoryEntry",
    "StorageMemoryWindow", 
    "StorageMemoryStats",
]
