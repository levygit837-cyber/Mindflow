"""Storage-specific exceptions.

Provides hierarchical exception handling for all storage operations,
integrating with the global error system.
"""

from __future__ import annotations

from typing import Any


class StorageError(Exception):
    """Base exception for all storage operations."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": "StorageError",
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class DatabaseError(StorageError):
    """Database-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        query: str | None = None,
        params: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, error_code, details)
        self.query = query
        self.params = params
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        base_dict = super().to_dict()
        base_dict["error"] = "DatabaseError"
        if self.query:
            base_dict["query"] = self.query
        if self.params:
            base_dict["params"] = self.params
        return base_dict


class VectorError(StorageError):
    """Vector database-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        collection: str | None = None,
        vector_id: str | None = None
    ) -> None:
        super().__init__(message, error_code, details)
        self.collection = collection
        self.vector_id = vector_id
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        base_dict = super().to_dict()
        base_dict["error"] = "VectorError"
        if self.collection:
            base_dict["collection"] = self.collection
        if self.vector_id:
            base_dict["vector_id"] = self.vector_id
        return base_dict


class CacheError(StorageError):
    """Cache-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        key: str | None = None
    ) -> None:
        super().__init__(message, error_code, details)
        self.key = key
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        base_dict = super().to_dict()
        base_dict["error"] = "CacheError"
        if self.key:
            base_dict["key"] = self.key
        return base_dict


class ConnectionError(StorageError):
    """Connection pool and connectivity errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        pool_name: str | None = None,
        connection_id: str | None = None
    ) -> None:
        super().__init__(message, error_code, details)
        self.pool_name = pool_name
        self.connection_id = connection_id
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        base_dict = super().to_dict()
        base_dict["error"] = "ConnectionError"
        if self.pool_name:
            base_dict["pool_name"] = self.pool_name
        if self.connection_id:
            base_dict["connection_id"] = self.connection_id
        return base_dict


class MigrationError(StorageError):
    """Database migration errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        from_version: str | None = None,
        to_version: str | None = None
    ) -> None:
        super().__init__(message, error_code, details)
        self.from_version = from_version
        self.to_version = to_version
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        base_dict = super().to_dict()
        base_dict["error"] = "MigrationError"
        if self.from_version:
            base_dict["from_version"] = self.from_version
        if self.to_version:
            base_dict["to_version"] = self.to_version
        return base_dict


# Convenience functions for error handling
def handle_storage_error(func):
    """Decorator for handling storage errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except StorageError:
            raise  # Re-raise storage errors
        except Exception as e:
            raise StorageError(
                message=f"Unexpected error in {func.__name__}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                details={"original_error": str(e), "function": func.__name__}
            ) from e
    return wrapper


def handle_database_error(func):
    """Decorator for handling database errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DatabaseError:
            raise  # Re-raise database errors
        except Exception as e:
            raise DatabaseError(
                message=f"Database error in {func.__name__}: {str(e)}",
                error_code="UNEXPECTED_DB_ERROR",
                details={"original_error": str(e), "function": func.__name__}
            ) from e
    return wrapper


def handle_vector_error(func):
    """Decorator for handling vector database errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VectorError:
            raise  # Re-raise vector errors
        except Exception as e:
            raise VectorError(
                message=f"Vector database error in {func.__name__}: {str(e)}",
                error_code="UNEXPECTED_VECTOR_ERROR",
                details={"original_error": str(e), "function": func.__name__}
            ) from e
    return wrapper
