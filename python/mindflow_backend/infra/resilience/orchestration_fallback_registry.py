"""Orchestration Fallback Registry - Registry for orchestration component fallback handlers.

This module provides a registry for fallback handlers specifically for
orchestration components, allowing prioritization and validation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class OrchestrationFallbackRegistry:
    """Registry for orchestration component fallback handlers.

    Allows prioritization and validation of fallback strategies for
    orchestration components (routing, delegation, teams, communication).
    """

    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = defaultdict(list)

    def register(
        self,
        component: str,
        handler: Callable,
        priority: int = 0,
    ) -> None:
        """Register a fallback handler for a component.

        Args:
            component: Component identifier (e.g., "intelligent_router")
            handler: Async callable that executes the fallback
            priority: Handler priority (higher = tried first)
        """
        self._handlers[component].append((priority, handler))
        # Sort by priority (descending)
        self._handlers[component].sort(key=lambda x: x[0], reverse=True)

        _logger.info(
            "orchestration_fallback_handler_registered",
            component=component,
            priority=priority,
            handlers_count=len(self._handlers[component]),
        )

    def get_handler(self, component: str) -> Callable | None:
        """Get the highest priority fallback handler for a component.

        Args:
            component: Component identifier

        Returns:
            Handler callable or None if not registered
        """
        handlers = self._handlers.get(component)
        if not handlers:
            return None

        # Return highest priority handler
        return handlers[0][1]

    def get_all_handlers(self, component: str) -> list[tuple[int, Callable]]:
        """Get all fallback handlers for a component sorted by priority.

        Args:
            component: Component identifier

        Returns:
            List of (priority, handler) tuples sorted by priority descending
        """
        return self._handlers.get(component, [])

    def list_components(self) -> list[str]:
        """List all components with registered fallback handlers.

        Returns:
            List of component identifiers
        """
        return list(self._handlers.keys())

    def unregister(self, component: str, handler: Callable | None = None) -> None:
        """Unregister fallback handler(s) for a component.

        Args:
            component: Component identifier
            handler: Specific handler to remove (None = remove all)
        """
        if handler is None:
            # Remove all handlers for component
            if component in self._handlers:
                del self._handlers[component]
                _logger.info(
                    "orchestration_all_fallback_handlers_unregistered",
                    component=component,
                )
        else:
            # Remove specific handler
            handlers = self._handlers.get(component, [])
            self._handlers[component] = [
                (p, h) for p, h in handlers if h != handler
            ]
            _logger.info(
                "orchestration_fallback_handler_unregistered",
                component=component,
                remaining_handlers=len(self._handlers[component]),
            )

    def validate_handler(self, handler: Callable) -> bool:
        """Validate that a handler is a valid async callable.

        Args:
            handler: Handler to validate

        Returns:
            True if valid, False otherwise
        """
        if not callable(handler):
            _logger.warning("orchestration_handler_not_callable")
            return False

        # Check if handler is async
        if not hasattr(handler, "__call__"):
            _logger.warning("orchestration_handler_not_callable")
            return False

        # Note: We can't fully validate async without calling it
        # This is a basic validation
        return True


# Global instance
_orchestration_fallback_registry: OrchestrationFallbackRegistry | None = None


def get_orchestration_fallback_registry() -> OrchestrationFallbackRegistry:
    """Get or create the global orchestration fallback registry instance."""
    global _orchestration_fallback_registry
    if _orchestration_fallback_registry is None:
        _orchestration_fallback_registry = OrchestrationFallbackRegistry()
        _logger.info("orchestration_fallback_registry_initialized")
    return _orchestration_fallback_registry
