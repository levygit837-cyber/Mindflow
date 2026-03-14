"""Database storage interfaces.

Extends core database interface with storage-specific contracts
and repository patterns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from uuid import UUID


class DatabaseRepositoryInterface(ABC):
    """Interface for database repositories."""
    
    @abstractmethod
    async def create(self, **kwargs) -> Any:
        """Create entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: Union[str, UUID, int]) -> Optional[Any]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_by_field(self, field_name: str, value: Any) -> List[Any]:
        """Get entities by field value."""
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
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None
    ) -> List[Any]:
        """List entities with filtering and pagination."""
        pass
    
    @abstractmethod
    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count entities with filters."""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: Union[str, UUID, int]) -> bool:
        """Check if entity exists."""
        pass
    
    @abstractmethod
    async def bulk_create(self, entities: List[Dict[str, Any]]) -> List[Any]:
        """Bulk create entities."""
        pass
    
    @abstractmethod
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> List[Any]:
        """Bulk update entities."""
        pass
    
    @abstractmethod
    async def bulk_delete(self, entity_ids: List[Union[str, UUID, int]]) -> int:
        """Bulk delete entities."""
        pass


class TransactionManagerInterface(ABC):
    """Interface for transaction management."""
    
    @abstractmethod
    async def begin_transaction(self, isolation_level: Optional[str] = None) -> Any:
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
    
    @abstractmethod
    async def savepoint(self, transaction: Any, name: str) -> Any:
        """Create savepoint."""
        pass
    
    @abstractmethod
    async def rollback_to_savepoint(self, transaction: Any, savepoint: Any) -> None:
        """Rollback to savepoint."""
        pass


class QueryBuilderInterface(ABC):
    """Interface for query builders."""
    
    @abstractmethod
    def select(self, table: str, columns: Optional[List[str]] = None) -> Any:
        """Build SELECT query."""
        pass
    
    @abstractmethod
    def insert(self, table: str, data: Dict[str, Any]) -> Any:
        """Build INSERT query."""
        pass
    
    @abstractmethod
    def update(self, table: str, data: Dict[str, Any], where: Optional[Dict[str, Any]] = None) -> Any:
        """Build UPDATE query."""
        pass
    
    @abstractmethod
    def delete(self, table: str, where: Optional[Dict[str, Any]] = None) -> Any:
        """Build DELETE query."""
        pass
    
    @abstractmethod
    def where(self, conditions: Dict[str, Any]) -> Any:
        """Add WHERE conditions."""
        pass
    
    @abstractmethod
    def join(self, table: str, on: str, join_type: Optional[str] = None) -> Any:
        """Add JOIN clause."""
        pass
    
    @abstractmethod
    def order_by(self, column: str, direction: str = "ASC") -> Any:
        """Add ORDER BY clause."""
        pass
    
    @abstractmethod
    def limit(self, count: int) -> Any:
        """Add LIMIT clause."""
        pass
    
    @abstractmethod
    def offset(self, count: int) -> Any:
        """Add OFFSET clause."""
        pass
    
    @abstractmethod
    def build(self) -> tuple[str, Dict[str, Any]]:
        """Build final query and parameters."""
        pass


class DatabaseMigrationInterface(ABC):
    """Interface for database migrations."""
    
    @abstractmethod
    async def create_migration_table(self) -> None:
        """Create migrations tracking table."""
        pass
    
    @abstractmethod
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        pass
    
    @abstractmethod
    async def mark_migration_applied(self, migration_id: str, checksum: str) -> None:
        """Mark migration as applied."""
        pass
    
    @abstractmethod
    async def get_pending_migrations(self, migrations_dir: str) -> List[Dict[str, Any]]:
        """Get pending migrations."""
        pass
    
    @abstractmethod
    async def apply_migration(self, migration: Dict[str, Any]) -> None:
        """Apply single migration."""
        pass
    
    @abstractmethod
    async def rollback_migration(self, migration_id: str) -> None:
        """Rollback migration."""
        pass


class DatabaseHealthInterface(ABC):
    """Interface for database health checks."""
    
    @abstractmethod
    async def check_connection(self) -> Dict[str, Any]:
        """Check database connection."""
        pass
    
    @abstractmethod
    async def check_performance(self) -> Dict[str, Any]:
        """Check database performance."""
        pass
    
    @abstractmethod
    async def check_integrity(self) -> Dict[str, Any]:
        """Check database integrity."""
        pass
    
    @abstractmethod
    async def check_space(self) -> Dict[str, Any]:
        """Check database space usage."""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get database metrics."""
        pass
