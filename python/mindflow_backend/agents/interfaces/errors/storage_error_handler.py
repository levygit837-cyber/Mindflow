"""Storage error handler interface.

Defines contracts for handling storage-related errors including
database failures, connection issues, and data integrity problems.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, Union
from abc import abstractmethod

from mindflow_backend.schemas.errors import (
    DatabaseErrorSchema,
    ConnectionErrorSchema,
    MigrationErrorSchema,
    VectorStoreErrorSchema,
    CacheErrorSchema,
    ErrorCategory,
    ErrorSeverity,
)

from .base_error_handler import BaseErrorHandlerContract


@runtime_checkable
class StorageErrorHandlerContract(BaseErrorHandlerContract, Protocol):
    """Contract for storage-related error handling.
    
    Specialized interface for handling errors from database operations,
    vector stores, caching systems, and data storage components.
    """

    @abstractmethod
    async def handle_database_error(
        self,
        exception: Exception,
        *,
        query: Optional[str] = None,
        table: Optional[str] = None,
        operation: Optional[str] = None,
        connection_id: Optional[str] = None,
        database: Optional[str] = None,
        **context: Any,
    ) -> DatabaseErrorSchema:
        """Handle database-specific errors.
        
        Args:
            exception: The database exception
            query: SQL query that failed
            table: Table involved in operation
            operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
            connection_id: Database connection identifier
            database: Database name
            **context: Additional context
            
        Returns:
            Database error schema with specific context
        """
        ...

    @abstractmethod
    async def handle_connection_error(
        self,
        exception: Exception,
        *,
        endpoint: Optional[str] = None,
        connection_string: Optional[str] = None,
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
        service: Optional[str] = None,
        **context: Any,
    ) -> ConnectionErrorSchema:
        """Handle database connection errors.
        
        Args:
            exception: The connection exception
            endpoint: Connection endpoint
            connection_string: Connection string (sanitized)
            timeout: Connection timeout
            retry_count: Number of retry attempts
            service: Service being connected to
            **context: Additional context
            
        Returns:
            Connection error schema with connection context
        """
        ...

    @abstractmethod
    async def handle_migration_error(
        self,
        exception: Exception,
        *,
        migration_file: Optional[str] = None,
        migration_version: Optional[str] = None,
        target_version: Optional[str] = None,
        current_version: Optional[str] = None,
        direction: Optional[str] = None,
        **context: Any,
    ) -> MigrationErrorSchema:
        """Handle database migration errors.
        
        Args:
            exception: The migration exception
            migration_file: Migration file that failed
            migration_version: Migration version
            target_version: Target database version
            current_version: Current database version
            direction: Migration direction (up/down)
            **context: Additional context
            
        Returns:
            Migration error schema with migration context
        """
        ...

    @abstractmethod
    async def handle_vector_store_error(
        self,
        exception: Exception,
        *,
        operation: Optional[str] = None,
        collection: Optional[str] = None,
        vector_dimension: Optional[int] = None,
        index_name: Optional[str] = None,
        query_type: Optional[str] = None,
        **context: Any,
    ) -> VectorStoreErrorSchema:
        """Handle vector store operation errors.
        
        Args:
            exception: The vector store exception
            operation: Vector operation (insert, search, delete)
            collection: Vector collection name
            vector_dimension: Vector dimension
            index_name: Index being used
            query_type: Type of vector query
            **context: Additional context
            
        Returns:
            Vector store error schema with vector context
        """
        ...

    @abstractmethod
    async def handle_cache_error(
        self,
        exception: Exception,
        *,
        cache_key: Optional[str] = None,
        cache_operation: Optional[str] = None,
        cache_backend: Optional[str] = None,
        ttl: Optional[int] = None,
        cache_size: Optional[int] = None,
        **context: Any,
    ) -> CacheErrorSchema:
        """Handle cache operation errors.
        
        Args:
            exception: The cache exception
            cache_key: Cache key involved
            cache_operation: Cache operation (get, set, delete)
            cache_backend: Cache backend (Redis, Memcached, etc.)
            ttl: Cache TTL
            cache_size: Cache size information
            **context: Additional context
            
        Returns:
            Cache error schema with cache context
        """
        ...

    @abstractmethod
    def get_database_health_status(
        self,
        database: Optional[str] = None,
        connection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get database health status for error context.
        
        Args:
            database: Database name to check
            connection_id: Specific connection to check
            
        Returns:
            Database health status information
        """
        ...

    @abstractmethod
    def should_retry_database_operation(
        self,
        exception: Exception,
        operation: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> bool:
        """Determine if a database operation should be retried.
        
        Args:
            exception: The database exception
            operation: Database operation type
            retry_count: Current retry count
            
        Returns:
            True if operation should be retried
        """
        ...

    @abstractmethod
    def get_fallback_database(
        self,
        primary_database: str,
        operation: Optional[str] = None,
    ) -> Optional[str]:
        """Get fallback database for high availability.
        
        Args:
            primary_database: Primary database that failed
            operation: Database operation type
            
        Returns:
            Fallback database name or None
        """
        ...

    @abstractmethod
    async def repair_connection(
        self,
        connection_id: str,
        *,
        force_reconnect: bool = False,
        timeout: Optional[float] = None,
    ) -> bool:
        """Attempt to repair a broken database connection.
        
        Args:
            connection_id: Connection identifier to repair
            force_reconnect: Force full reconnection
            timeout: Repair operation timeout
            
        Returns:
            True if connection was successfully repaired
        """
        ...

    @abstractmethod
    def estimate_data_loss(
        self,
        exception: Exception,
        operation: Optional[str] = None,
        table: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Estimate potential data loss from storage error.
        
        Args:
            exception: The storage exception
            operation: Operation that failed
            table: Table involved (if applicable)
            
        Returns:
            Data loss estimation information
        """
        ...

    # Storage-specific convenience methods
    
    def get_connection_pool_status(self, backend: str) -> Dict[str, Any]:
        """Get connection pool status for a storage backend.
        
        Args:
            backend: Storage backend name
            
        Returns:
            Connection pool status information
        """
        # Default implementation - subclasses should override
        return {
            "backend": backend,
            "active_connections": 0,
            "idle_connections": 0,
            "total_connections": 0,
            "max_connections": 0,
            "status": "unknown",
        }

    def get_cache_statistics(self, backend: str) -> Dict[str, Any]:
        """Get cache statistics for monitoring.
        
        Args:
            backend: Cache backend name
            
        Returns:
            Cache statistics
        """
        # Default implementation - subclasses should override
        return {
            "backend": backend,
            "hits": 0,
            "misses": 0,
            "hit_rate": 0.0,
            "size": 0,
            "max_size": 0,
            "evictions": 0,
        }

    def validate_storage_configuration(
        self,
        backend: str,
        configuration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate storage backend configuration.
        
        Args:
            backend: Storage backend name
            configuration: Configuration to validate
            
        Returns:
            Validation results
        """
        # Default implementation - subclasses should override
        return {
            "backend": backend,
            "valid": True,
            "errors": [],
            "warnings": [],
        }
