"""Database storage interfaces.

Extends core database interface with storage-specific contracts
and repository patterns.
"""

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class DatabaseRepositoryInterface(ABC):
    """Interface for database repositories."""
    
    @abstractmethod
    async def create(self, **kwargs) -> Any:
        """Create entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str | UUID | int) -> Any | None:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_by_field(self, field_name: str, value: Any) -> builtins.list[Any]:
        """Get entities by field value."""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str | UUID | int, **kwargs) -> Any | None:
        """Update entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str | UUID | int) -> bool:
        """Delete entity."""
        pass
    
    @abstractmethod
    async def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        order_direction: str | None = None
    ) -> builtins.list[Any]:
        """List entities with filtering and pagination."""
        pass
    
    @abstractmethod
    async def count(
        self,
        filters: dict[str, Any] | None = None
    ) -> int:
        """Count entities with filters."""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str | UUID | int) -> bool:
        """Check if entity exists."""
        pass
    
    @abstractmethod
    async def bulk_create(self, entities: builtins.list[dict[str, Any]]) -> builtins.list[Any]:
        """Bulk create entities."""
        pass
    
    @abstractmethod
    async def bulk_update(self, updates: builtins.list[dict[str, Any]]) -> builtins.list[Any]:
        """Bulk update entities."""
        pass
    
    @abstractmethod
    async def bulk_delete(self, entity_ids: builtins.list[str | UUID | int]) -> int:
        """Bulk delete entities."""
        pass


class TransactionManagerInterface(ABC):
    """Interface for transaction management."""
    
    @abstractmethod
    async def begin_transaction(self, isolation_level: str | None = None) -> Any:
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
    def select(self, table: str, columns: list[str] | None = None) -> Any:
        """Build SELECT query."""
        pass
    
    @abstractmethod
    def insert(self, table: str, data: dict[str, Any]) -> Any:
        """Build INSERT query."""
        pass
    
    @abstractmethod
    def update(self, table: str, data: dict[str, Any], where: dict[str, Any] | None = None) -> Any:
        """Build UPDATE query."""
        pass
    
    @abstractmethod
    def delete(self, table: str, where: dict[str, Any] | None = None) -> Any:
        """Build DELETE query."""
        pass
    
    @abstractmethod
    def where(self, conditions: dict[str, Any]) -> Any:
        """Add WHERE conditions."""
        pass
    
    @abstractmethod
    def join(self, table: str, on: str, join_type: str | None = None) -> Any:
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
    def build(self) -> tuple[str, dict[str, Any]]:
        """Build final query and parameters."""
        pass


class DatabaseMigrationInterface(ABC):
    """Interface for database migrations."""
    
    @abstractmethod
    async def create_migration_table(self) -> None:
        """Create migrations tracking table."""
        pass
    
    @abstractmethod
    async def get_applied_migrations(self) -> list[str]:
        """Get list of applied migrations."""
        pass
    
    @abstractmethod
    async def mark_migration_applied(self, migration_id: str, checksum: str) -> None:
        """Mark migration as applied."""
        pass
    
    @abstractmethod
    async def get_pending_migrations(self, migrations_dir: str) -> list[dict[str, Any]]:
        """Get pending migrations."""
        pass
    
    @abstractmethod
    async def apply_migration(self, migration: dict[str, Any]) -> None:
        """Apply single migration."""
        pass
    
    @abstractmethod
    async def rollback_migration(self, migration_id: str) -> None:
        """Rollback migration."""
        pass


class DatabaseHealthInterface(ABC):
    """Interface for database health checks."""
    
    @abstractmethod
    async def check_connection(self) -> dict[str, Any]:
        """Check database connection."""
        pass
    
    @abstractmethod
    async def check_performance(self) -> dict[str, Any]:
        """Check database performance."""
        pass
    
    @abstractmethod
    async def check_integrity(self) -> dict[str, Any]:
        """Check database integrity."""
        pass
    
    @abstractmethod
    async def check_space(self) -> dict[str, Any]:
        """Check database space usage."""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> dict[str, Any]:
        """Get database metrics."""
        pass
