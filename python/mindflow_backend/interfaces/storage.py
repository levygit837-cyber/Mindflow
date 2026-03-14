"""Storage interfaces for MindFlow backend.

Provides unified storage contracts that integrate with global
interface system and provide storage-specific abstractions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from uuid import UUID
from datetime import datetime

from mindflow_backend.interfaces.core.base import BaseComponentInterface


class StorageBackendInterface(BaseComponentInterface):
    """Interface for storage backend implementations."""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize storage backend with configuration."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown storage backend gracefully."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics and statistics."""
        pass
    
    @abstractmethod
    async def configure(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update storage configuration."""
        pass


class StorageOperationInterface(ABC):
    """Interface for storage operations."""
    
    @abstractmethod
    async def execute(
        self,
        operation: str,
        payload: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute storage operation."""
        pass
    
    @abstractmethod
    async def batch_execute(
        self,
        operations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute batch operations."""
        pass
    
    @abstractmethod
    async def validate_operation(
        self,
        operation: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate storage operation."""
        pass


class StorageQueryInterface(ABC):
    """Interface for storage queries."""
    
    @abstractmethod
    async def query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute storage query."""
        pass
    
    @abstractmethod
    async def query_with_pagination(
        self,
        query: str,
        page: int = 1,
        page_size: int = 50,
        parameters: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute paginated query."""
        pass
    
    @abstractmethod
    async def count(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count query results."""
        pass


class StorageTransactionInterface(ABC):
    """Interface for storage transactions."""
    
    @abstractmethod
    async def begin_transaction(
        self,
        isolation_level: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> str:
        """Begin storage transaction."""
        pass
    
    @abstractmethod
    async def commit_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Commit storage transaction."""
        pass
    
    @abstractmethod
    async def rollback_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Rollback storage transaction."""
        pass
    
    @abstractmethod
    async def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction status."""
        pass


class StorageIndexInterface(ABC):
    """Interface for storage indexing."""
    
    @abstractmethod
    async def create_index(
        self,
        index_name: str,
        fields: List[str],
        index_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create storage index."""
        pass
    
    @abstractmethod
    async def drop_index(self, index_name: str) -> Dict[str, Any]:
        """Drop storage index."""
        pass
    
    @abstractmethod
    async def list_indexes(self) -> List[Dict[str, Any]]:
        """List storage indexes."""
        pass
    
    @abstractmethod
    async def optimize_indexes(self) -> Dict[str, Any]:
        """Optimize storage indexes."""
        pass


class StorageBackupInterface(ABC):
    """Interface for storage backup operations."""
    
    @abstractmethod
    async def create_backup(
        self,
        backup_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create storage backup."""
        pass
    
    @abstractmethod
    async def restore_backup(
        self,
        backup_id: str,
        restore_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Restore storage backup."""
        pass
    
    @abstractmethod
    async def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        pass
    
    @abstractmethod
    async def delete_backup(self, backup_id: str) -> Dict[str, Any]:
        """Delete storage backup."""
        pass


class StorageMigrationInterface(ABC):
    """Interface for storage migrations."""
    
    @abstractmethod
    async def migrate_data(
        self,
        source_config: Dict[str, Any],
        target_config: Dict[str, Any],
        migration_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Migrate storage data."""
        pass
    
    @abstractmethod
    async def validate_migration(
        self,
        migration_id: str
    ) -> Dict[str, Any]:
        """Validate storage migration."""
        pass
    
    @abstractmethod
    async def rollback_migration(
        self,
        migration_id: str
    ) -> Dict[str, Any]:
        """Rollback storage migration."""
        pass


class StorageMonitoringInterface(ABC):
    """Interface for storage monitoring."""
    
    @abstractmethod
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        pass
    
    @abstractmethod
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        pass
    
    @abstractmethod
    async def set_alert_thresholds(
        self,
        thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set monitoring alert thresholds."""
        pass
    
    @abstractmethod
    async def get_alerts(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get monitoring alerts."""
        pass
