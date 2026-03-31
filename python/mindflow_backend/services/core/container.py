"""Dependency injection container for core services.

This module provides a centralized container for managing service dependencies
and implementing proper dependency injection patterns.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypeVar

T = TypeVar('T')


class ServiceContainer:
    """Dependency injection container for services.
    
    Provides singleton pattern with lazy loading and proper lifecycle management
    for all services in the application.
    """
    
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._singletons: dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def register_factory(
        self,
        service_name: str,
        factory: Callable[[], T],
        singleton: bool = True
    ) -> None:
        """Register a service factory.
        
        Args:
            service_name: Name of the service
            factory: Factory function to create service
            singleton: Whether service should be singleton
        """
        with self._lock:
            self._factories[service_name] = factory
            if singleton and service_name not in self._singletons:
                self._singletons[service_name] = None
    
    def register_instance(self, service_name: str, instance: T) -> None:
        """Register a service instance.
        
        Args:
            service_name: Name of the service
            instance: Service instance
        """
        with self._lock:
            self._services[service_name] = instance
            self._singletons[service_name] = instance
    
    def get(self, service_name: str) -> T:
        """Get service instance.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
        """
        with self._lock:
            # Return existing instance if available
            if service_name in self._services:
                return self._services[service_name]
            
            # Create singleton if needed
            if service_name in self._singletons and self._singletons[service_name] is not None:
                return self._singletons[service_name]
            
            # Create new instance using factory
            if service_name in self._factories:
                instance = self._factories[service_name]()
                
                # Store as singleton if configured
                if service_name in self._singletons:
                    self._singletons[service_name] = instance
                    self._services[service_name] = instance
                
                return instance
            
            raise KeyError(f"Service '{service_name}' not registered")
    
    def has(self, service_name: str) -> bool:
        """Check if service is registered.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if service is registered
        """
        with self._lock:
            return service_name in self._services or service_name in self._factories
    
    def clear(self) -> None:
        """Clear all registered services."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
    
    async def shutdown(self) -> None:
        """Shutdown all services with cleanup."""
        with self._lock:
            # Call shutdown on services that support it
            for service in self._services.values():
                if hasattr(service, 'shutdown') and callable(service.shutdown):
                    try:
                        await service.shutdown()
                    except Exception:
                        pass  # Ignore shutdown errors
            
            self.clear()


# Global container instance
_container: ServiceContainer | None = None
_container_lock = threading.Lock()


def get_container() -> ServiceContainer:
    """Get global service container."""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = ServiceContainer()
    return _container


def register_service(
    service_name: str,
    factory: Callable[[], T],
    singleton: bool = True
) -> None:
    """Register a service in the global container.
    
    Args:
        service_name: Name of the service
        factory: Factory function to create service
        singleton: Whether service should be singleton
    """
    container = get_container()
    container.register_factory(service_name, factory, singleton)


def get_service(service_name: str) -> T:
    """Get service from global container.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Service instance
    """
    container = get_container()
    return container.get(service_name)


# Decorator for automatic service registration
def service(name: str, singleton: bool = True):
    """Decorator for automatic service registration.
    
    Args:
        name: Service name
        singleton: Whether service should be singleton
    """
    def decorator(cls):
        def factory():
            return cls()
        register_service(name, factory, singleton)
        return cls
    return decorator


# Initialize core services
def initialize_core_services() -> None:
    """Initialize all core services in the container."""
    from mindflow_backend.memory import get_memory_service
    from mindflow_backend.services.core import (
        get_agent_service,
        get_provider_service,
        get_session_service,
    )
    
    container = get_container()
    
    # Register core services
    container.register_factory("agent_service", get_agent_service)
    container.register_factory("session_service", get_session_service)
    container.register_factory("memory_service", get_memory_service)
    container.register_factory("provider_service", get_provider_service)


# Lazy initialization
@lru_cache(maxsize=1)
def get_initialized_container() -> ServiceContainer:
    """Get initialized container with core services."""
    initialize_core_services()
    return get_container()
