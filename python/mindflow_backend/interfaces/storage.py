"""Storage interfaces for MindFlow backend.

Provides unified storage contracts that integrate with global
interface system and provide storage-specific abstractions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from mindflow_backend.interfaces.core.base import BaseComponentInterface


class StorageBackendInterface(BaseComponentInterface):
    """Interface for storage backend implementations."""
    
    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize storage backend with configuration."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown storage backend gracefully."""
        pass
    
    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check."""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> dict[str, Any]:
        """Get storage metrics and statistics."""
        pass
    
    @abstractmethod
    async def configure(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update storage configuration."""
        pass


class StorageOperationInterface(ABC):
    """Interface for storage operations."""
    
    @abstractmethod
    async def execute(
        self,
        operation: str,
        payload: dict[str, Any],
        options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute storage operation."""
        pass
    
    @abstractmethod
    async def batch_execute(
        self,
        operations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Execute batch operations."""
        pass
    
    @abstractmethod
    async def validate_operation(
        self,
        operation: str,
        payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate storage operation."""
        pass


class StorageQueryInterface(ABC):
    """Interface for storage queries."""
    
    @abstractmethod
    async def query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute storage query."""
        pass
    
    @abstractmethod
    async def query_with_pagination(
        self,
        query: str,
        page: int = 1,
        page_size: int = 50,
        parameters: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute paginated query."""
        pass
    
    @abstractmethod
    async def count(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None
    ) -> int:
        """Count query results."""
        pass


class StorageTransactionInterface(ABC):
    """Interface for storage transactions."""
    
    @abstractmethod
    async def begin_transaction(
        self,
        isolation_level: str | None = None,
        timeout_seconds: int | None = None
    ) -> str:
        """Begin storage transaction."""
        pass
    
    @abstractmethod
    async def commit_transaction(self, transaction_id: str) -> dict[str, Any]:
        """Commit storage transaction."""
        pass
    
    @abstractmethod
    async def rollback_transaction(self, transaction_id: str) -> dict[str, Any]:
        """Rollback storage transaction."""
        pass
    
    @abstractmethod
    async def get_transaction_status(self, transaction_id: str) -> dict[str, Any]:
        """Get transaction status."""
        pass


class StorageIndexInterface(ABC):
    """Interface for storage indexing."""
    
    @abstractmethod
    async def create_index(
        self,
        index_name: str,
        fields: list[str],
        index_config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create storage index."""
        pass
    
    @abstractmethod
    async def drop_index(self, index_name: str) -> dict[str, Any]:
        """Drop storage index."""
        pass
    
    @abstractmethod
    async def list_indexes(self) -> list[dict[str, Any]]:
        """List storage indexes."""
        pass
    
    @abstractmethod
    async def optimize_indexes(self) -> dict[str, Any]:
        """Optimize storage indexes."""
        pass


class StorageBackupInterface(ABC):
    """Interface for storage backup operations."""
    
    @abstractmethod
    async def create_backup(
        self,
        backup_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create storage backup."""
        pass
    
    @abstractmethod
    async def restore_backup(
        self,
        backup_id: str,
        restore_config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Restore storage backup."""
        pass
    
    @abstractmethod
    async def list_backups(self) -> list[dict[str, Any]]:
        """List available backups."""
        pass
    
    @abstractmethod
    async def delete_backup(self, backup_id: str) -> dict[str, Any]:
        """Delete storage backup."""
        pass


class StorageMigrationInterface(ABC):
    """Interface for storage migrations."""
    
    @abstractmethod
    async def migrate_data(
        self,
        source_config: dict[str, Any],
        target_config: dict[str, Any],
        migration_options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Migrate storage data."""
        pass
    
    @abstractmethod
    async def validate_migration(
        self,
        migration_id: str
    ) -> dict[str, Any]:
        """Validate storage migration."""
        pass
    
    @abstractmethod
    async def rollback_migration(
        self,
        migration_id: str
    ) -> dict[str, Any]:
        """Rollback storage migration."""
        pass


class StorageMonitoringInterface(ABC):
    """Interface for storage monitoring."""
    
    @abstractmethod
    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        pass
    
    @abstractmethod
    async def get_health_status(self) -> dict[str, Any]:
        """Get health status."""
        pass
    
    @abstractmethod
    async def get_usage_statistics(self) -> dict[str, Any]:
        """Get usage statistics."""
        pass
    
    @abstractmethod
    async def set_alert_thresholds(
        self,
        thresholds: dict[str, Any]
    ) -> dict[str, Any]:
        """Set monitoring alert thresholds."""
        pass
    
    @abstractmethod
    async def get_alerts(self, since: datetime | None = None) -> list[dict[str, Any]]:
        """Get monitoring alerts."""
        pass
