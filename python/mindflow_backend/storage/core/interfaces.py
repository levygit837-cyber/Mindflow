"""Core storage interfaces and abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from uuid import UUID
from datetime import datetime


class StorageInterface(ABC):
    """Base interface for all storage implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage connection."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close storage connection."""
        pass


class DatabaseInterface(StorageInterface):
    """Interface for relational database operations."""
    
    @abstractmethod
    async def get_session(self) -> AsyncGenerator[Any, None]:
        """Get database session."""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute raw query."""
        pass
    
    @abstractmethod
    async def begin_transaction(self) -> Any:
        """Begin transaction."""
        pass
    
    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> None:
        """Commit transaction."""
        pass
    
    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback transaction."""
        pass


class VectorDatabaseInterface(StorageInterface):
    """Interface for vector database operations."""
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create vector collection."""
        pass
    
    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert vectors into collection."""
        pass
    
    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> None:
        """Delete vectors by ID."""
        pass
    
    @abstractmethod
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific vector by ID."""
        pass
    
    @abstractmethod
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update vector and metadata."""
        pass


class CacheInterface(StorageInterface):
    """Interface for cache operations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache."""
        pass


class RepositoryInterface(ABC):
    """Base interface for repositories."""
    
    @abstractmethod
    async def create(self, **kwargs) -> Any:
        """Create entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: Union[str, UUID, int]) -> Optional[Any]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def update(self, entity_id: Union[str, UUID, int], **kwargs) -> Optional[Any]:
        """Update entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: Union[str, UUID, int]) -> bool:
        """Delete entity."""
        pass
    
    @abstractmethod
    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Any]:
        """List entities with optional filters."""
        pass


class ConnectionPoolInterface(ABC):
    """Interface for connection pool management."""
    
    @abstractmethod
    async def get_connection(self) -> Any:
        """Get connection from pool."""
        pass
    
    @abstractmethod
    async def return_connection(self, connection: Any) -> None:
        """Return connection to pool."""
        pass
    
    @abstractmethod
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        pass
    
    @abstractmethod
    async def close_all(self) -> None:
        """Close all connections."""
        pass


class MigrationInterface(ABC):
    """Interface for database migrations."""
    
    @abstractmethod
    async def migrate_up(self, target_version: Optional[str] = None) -> None:
        """Run migrations up to target version."""
        pass
    
    @abstractmethod
    async def migrate_down(self, target_version: str) -> None:
        """Migrate down to target version."""
        pass
    
    @abstractmethod
    async def get_current_version(self) -> str:
        """Get current migration version."""
        pass
    
    @abstractmethod
    async def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations."""
        pass
