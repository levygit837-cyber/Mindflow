"""Base service interfaces for OmniMind backend.

This module provides fundamental interfaces that all services should implement
to ensure consistency and proper error handling.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any
from abc import ABC, abstractmethod


@runtime_checkable
class BaseServiceInterface(Protocol):
    """Base interface for all services.
    
    Provides common functionality for logging, validation, and error handling
    that all services should implement.
    """
    
    def __init__(self) -> None:
        """Initialize service."""
        ...
    
    def log_operation(self, operation: str, **kwargs) -> None:
        """Log service operation with context.
        
        Args:
            operation: Name of the operation being performed
            **kwargs: Additional context data for logging
        """
        ...
    
    def validate_input(self, data: Any, schema: type) -> bool:
        """Validate input data against schema.
        
        Args:
            data: Data to validate
            schema: Schema type to validate against
            
        Returns:
            True if validation passes, False otherwise
        """
        ...
    
    def handle_error(self, error: Exception, context: str = "") -> Any:
        """Handle service errors consistently.
        
        Args:
            error: Exception that occurred
            context: Additional context about where error occurred
            
        Returns:
            Error response or re-raises exception
        """
        ...


@runtime_checkable
class ServiceLifecycleInterface(Protocol):
    """Interface for service lifecycle management."""
    
    async def initialize(self) -> None:
        """Initialize service resources."""
        ...
    
    async def shutdown(self) -> None:
        """Cleanup service resources."""
        ...
    
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        ...


@runtime_checkable
class CacheableServiceInterface(Protocol):
    """Interface for services that support caching."""
    
    async def get_from_cache(self, key: str) -> Any | None:
        """Get value from cache."""
        ...
    
    async def set_cache(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ...
    
    async def invalidate_cache(self, pattern: str | None = None) -> None:
        """Invalidate cache entries."""
        ...


@runtime_checkable
class ConfigurableServiceInterface(Protocol):
    """Interface for services that support dynamic configuration."""
    
    def update_config(self, config: dict[str, Any]) -> None:
        """Update service configuration."""
        ...
    
    def get_config(self) -> dict[str, Any]:
        """Get current service configuration."""
        ...
    
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration changes."""
        ...


class BaseAbstractService(ABC):
    """Abstract base class implementing common service patterns.
    
    Services can inherit from this class to get default implementations
    of common functionality like logging and error handling.
    """
    
    def __init__(self) -> None:
        """Initialize base service."""
        self._logger = self._get_logger()
    
    @abstractmethod
    def _get_logger(self) -> Any:
        """Get logger instance for the service."""
        ...
    
    def log_operation(self, operation: str, **kwargs) -> None:
        """Log service operation."""
        self._logger.info(f"service_operation_{operation}", **kwargs)
    
    def validate_input(self, data: Any, schema: type) -> bool:
        """Default input validation."""
        try:
            # Basic validation - can be extended with pydantic or similar
            if hasattr(schema, 'model_validate'):
                schema.model_validate(data)
                return True
            return True
        except Exception:
            return False
    
    def handle_error(self, error: Exception, context: str = "") -> Any:
        """Default error handling."""
        self._logger.error(f"service_error_{context}", error=str(error))
        return {
            "status": "error",
            "error": str(error),
            "context": context
        }
