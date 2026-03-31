"""Storage interfaces.

Consolidates storage-related interfaces from the global interfaces system
and provides storage-specific extensions.
"""

# Import core storage interfaces
from mindflow_backend.interfaces.infrastructure.grpc import GrpcClient as GrpcClientInterface
from mindflow_backend.interfaces.infrastructure.grpc import GrpcServer as GrpcServerInterface

# Import global interfaces that relate to storage
from mindflow_backend.interfaces.services.memory import MemoryServiceInterface

from ..core.base import (
    BaseComponentInterface,
)
from ..core.config import (
    ConfigurableInterface,
)
from .cache import CacheManagerInterface

# Storage-specific extensions
from .database import DatabaseRepositoryInterface
from .memory import MemoryStoreInterface
from .vector import VectorStoreInterface

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
