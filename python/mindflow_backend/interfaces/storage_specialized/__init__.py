"""Storage interfaces.

Consolidates storage-related interfaces from the global interfaces system
and provides storage-specific extensions.
"""

# Import core storage interfaces
from ..core.base import (
    BaseComponentInterface,
)
from ..core.config import (
    ConfigurableInterface,
)

# Import global interfaces that relate to storage
from mindflow_backend.interfaces.services.memory import MemoryServiceInterface
from mindflow_backend.interfaces.infrastructure.grpc import GrpcClient as GrpcClientInterface, GrpcServer as GrpcServerInterface

# Storage-specific extensions
from .database import DatabaseRepositoryInterface
from .vector import VectorStoreInterface
from .cache import CacheManagerInterface
from .memory import MemoryStoreInterface

__all__ = [
    # Core interfaces
    "StorageInterface",
    "DatabaseInterface",
    "VectorDatabaseInterface", 
    "CacheInterface",
    "RepositoryInterface",
    "ConnectionPoolInterface",
    "MigrationInterface",
    
    # Global interfaces (storage-related)
    "MemoryServiceInterface",
    "GrpcClientInterface",
    "GrpcServerInterface",
    
    # Storage-specific interfaces
    "DatabaseRepositoryInterface",
    "VectorStoreInterface",
    "CacheManagerInterface",
    "MemoryStoreInterface",
]
