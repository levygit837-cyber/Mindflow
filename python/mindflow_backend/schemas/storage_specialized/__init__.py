"""Storage-specific schemas.

Integrates with global schema system while providing storage-specific
contracts and data structures.
"""

from .cache import (
    CacheConfig,
    CacheEntry,
    CacheStats,
)
from .database import (
    ConnectionConfig,
    DatabaseConfig,
    HealthCheckConfig,
    MigrationConfig,
    PoolConfig,
)
from .memory import (
    StorageMemoryEntry,
    StorageMemoryStats,
    StorageMemoryWindow,
)
from .vector import (
    VectorCollection,
    VectorConfig,
    VectorMetadata,
    VectorSearchRequest,
    VectorSearchResponse,
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
