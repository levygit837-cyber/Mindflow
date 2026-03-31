"""Dependency injection container for agent system.

Provides lightweight DI container to manage dependencies and
promote loose coupling between components.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mindflow_backend.exceptions import DependencyInjectionError


class DIContainer:
    """Simple dependency injection container."""
    
    def __init__(self) -> None:
        self._singletons: dict[type, Any] = {}
        self._factories: dict[type, Callable[[], Any]] = {}
        self._instances: dict[type, Any] = {}
    
    def register_singleton(self, interface: type, implementation: type) -> None:
        """Register a singleton implementation."""
        self._singletons[interface] = implementation
    
    def register_factory(self, interface: type, factory: Callable[[], Any]) -> None:
        """Register a factory function for creating instances."""
        self._factories[interface] = factory
    
    def register_instance(self, interface: type, instance: Any) -> None:
        """Register a specific instance."""
        self._instances[interface] = instance
    
    def get(self, interface: type) -> Any:
        """Get an instance of the requested interface."""
        # Check for pre-registered instance first
        if interface in self._instances:
            return self._instances[interface]
        
        # Check for singleton
        if interface in self._singletons:
            if interface not in self._instances:
                self._instances[interface] = self._singletons[interface]()
            return self._instances[interface]
        
        # Check for factory
        if interface in self._factories:
            return self._factories[interface]()
        
        raise DependencyInjectionError(
            f"No registration found for {interface.__name__}",
            dependency_type=interface.__name__
        )
    
    def has(self, interface: type) -> bool:
        """Check if interface is registered."""
        return (
            interface in self._instances or
            interface in self._singletons or
            interface in self._factories
        )
    
    def clear(self) -> None:
        """Clear all registrations (useful for testing)."""
        self._singletons.clear()
        self._factories.clear()
        self._instances.clear()


# Global container instance
_container = DIContainer()


def get_container() -> DIContainer:
    """Get the global DI container."""
    return _container


def register_singleton(interface: type, implementation: type) -> None:
    """Register a singleton in the global container."""
    _container.register_singleton(interface, implementation)


def register_factory(interface: type, factory: Callable[[], Any]) -> None:
    """Register a factory in the global container."""
    _container.register_factory(interface, factory)


def register_instance(interface: type, instance: Any) -> None:
    """Register an instance in the global container."""
    _container.register_instance(interface, instance)


def get(interface: type) -> Any:
    """Get an instance from the global container."""
    return _container.get(interface)
