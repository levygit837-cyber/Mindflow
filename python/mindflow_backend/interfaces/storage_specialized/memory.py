"""Memory storage interfaces.

Extends global memory interfaces with storage-specific contracts
and implementation patterns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mindflow_backend.interfaces.services.memory import MemoryServiceInterface

from ...schemas.storage_specialized.memory import (
    MemoryCleanupRequest,
    MemoryCleanupResponse,
    MemoryMigrationResponse,
    StorageMemoryEntry,
    StorageMemoryStats,
)


class MemoryStoreInterface(MemoryServiceInterface):
    """Storage-specific memory store interface."""
    
    @abstractmethod
    async def store_with_metadata(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        storage_metadata: dict[str, Any] | None = None
    ) -> StorageMemoryEntry:
        """Store memory with storage metadata."""
        pass
    
    @abstractmethod
    async def retrieve_storage_metadata(
        self,
        memory_id: str,
        include_storage_info: bool = True
    ) -> StorageMemoryEntry | None:
        """Retrieve memory with storage metadata."""
        pass
    
    @abstractmethod
    async def update_storage_metadata(
        self,
        memory_id: str,
        storage_metadata: dict[str, Any]
    ) -> StorageMemoryEntry | None:
        """Update storage metadata."""
        pass
    
    @abstractmethod
    async def get_storage_stats(self, session_id: str | None = None) -> StorageMemoryStats:
        """Get storage statistics."""
        pass


class MemoryPersistenceInterface(ABC):
    """Interface for memory persistence operations."""
    
    @abstractmethod
    async def backup_memory(
        self,
        backup_config: dict[str, Any]
    ) -> MemoryMigrationResponse:
        """Backup memory data."""
        pass
    
    @abstractmethod
    async def restore_memory(
        self,
        backup_path: str,
        restore_config: dict[str, Any] | None = None
    ) -> MemoryMigrationResponse:
        """Restore memory data."""
        pass
    
    @abstractmethod
    async def export_memory(
        self,
        export_format: str,
        filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Export memory data."""
        pass
    
    @abstractmethod
    async def import_memory(
        self,
        import_path: str,
        import_format: str,
        merge_strategy: str = "append"
    ) -> MemoryMigrationResponse:
        """Import memory data."""
        pass


class MemoryOptimizationInterface(ABC):
    """Interface for memory optimization operations."""
    
    @abstractmethod
    async def optimize_storage(
        self,
        optimization_type: str = "auto",
        target_backends: list[str] | None = None
    ) -> dict[str, Any]:
        """Optimize storage."""
        pass
    
    @abstractmethod
    async def compact_memory(
        self,
        session_id: str | None = None,
        older_than_days: int | None = None
    ) -> dict[str, Any]:
        """Compact memory data."""
        pass
    
    @abstractmethod
    async def reindex_memory(
        self,
        index_types: list[str] | None = None
    ) -> dict[str, Any]:
        """Reindex memory data."""
        pass
    
    @abstractmethod
    async def analyze_storage_efficiency(self) -> dict[str, Any]:
        """Analyze storage efficiency."""
        pass


class MemoryArchivingInterface(ABC):
    """Interface for memory archiving operations."""
    
    @abstractmethod
    async def archive_memory(
        self,
        archive_config: MemoryCleanupRequest
    ) -> MemoryCleanupResponse:
        """Archive memory data."""
        pass
    
    @abstractmethod
    async def retrieve_archived(
        self,
        archive_id: str,
        filters: dict[str, Any] | None = None
    ) -> list[StorageMemoryEntry]:
        """Retrieve archived memory."""
        pass
    
    @abstractmethod
    async def list_archives(
        self,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """List available archives."""
        pass
    
    @abstractmethod
    async def delete_archive(self, archive_id: str) -> bool:
        """Delete archive."""
        pass


class MemoryCompressionInterface(ABC):
    """Interface for memory compression operations."""
    
    @abstractmethod
    async def compress_memory(
        self,
        compression_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Compress memory data."""
        pass
    
    @abstractmethod
    async def decompress_memory(
        self,
        compressed_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Decompress memory data."""
        pass
    
    @abstractmethod
    async def get_compression_stats(self) -> dict[str, Any]:
        """Get compression statistics."""
        pass


class MemoryEncryptionInterface(ABC):
    """Interface for memory encryption operations."""
    
    @abstractmethod
    async def encrypt_memory(
        self,
        memory_data: dict[str, Any],
        encryption_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Encrypt memory data."""
        pass
    
    @abstractmethod
    async def decrypt_memory(
        self,
        encrypted_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Decrypt memory data."""
        pass
    
    @abstractmethod
    async def rotate_encryption_keys(
        self,
        rotation_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Rotate encryption keys."""
        pass
    
    @abstractmethod
    async def get_encryption_status(self) -> dict[str, Any]:
        """Get encryption status."""
        pass
