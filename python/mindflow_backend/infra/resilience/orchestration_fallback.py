"""Orchestration Fallback System - Component-level graceful degradation for MindFlow.

This module provides a fallback system specifically for orchestration components
(IntelligentRouter, DelegationEngine, TeamOrchestrator, CommunicationBus),
complementing the feature-level graceful degradation in infra/error_handling.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ComponentStatus(Enum):
    """Status of an orchestration component's fallback state."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FALLBACK_ACTIVE = "fallback_active"


@dataclass
class FallbackContext:
    """Context information for fallback execution."""
    component: str
    operation: str
    original_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FallbackResult:
    """Result of fallback execution."""
    success: bool
    result: Any
    fallback_used: bool
    component: str
    latency_seconds: float
    error: str | None = None


class OrchestrationFallbackManager:
    """Central manager for orchestration component fallback.

    Coordinates fallback activation, execution, and metrics collection
    for orchestration components (routing, delegation, teams, communication).

    Complements the feature-level GracefulDegradationManager in infra/error_handling.
    """

    def __init__(self):
        self._fallback_handlers: dict[str, Callable] = {}
        self._component_status: dict[str, ComponentStatus] = defaultdict(
            lambda: ComponentStatus.HEALTHY
        )
        self._metrics_collector: Any | None = None
        self._lock: asyncio.Lock | None = None
        self._retry_manager: Any | None = None

    def set_retry_manager(self, retry_manager: Any) -> None:
        """Set the retry manager instance."""
        self._retry_manager = retry_manager

    def _get_lock(self) -> asyncio.Lock:
        """Lazy-init asyncio lock for thread safety."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def set_metrics_collector(self, collector: Any) -> None:
        """Set the metrics collector instance."""
        self._metrics_collector = collector

    def register_fallback_handler(
        self,
        component: str,
        handler: Callable,
    ) -> None:
        """Register a fallback handler for a component.

        Args:
            component: Component identifier (e.g., "intelligent_router")
            handler: Async callable that executes the fallback
        """
        self._fallback_handlers[component] = handler
        _logger.info(
            "orchestration_fallback_handler_registered",
            component=component,
        )

    async def execute_with_fallback(
        self,
        component: str,
        primary_func: Callable,
        fallback_func: Callable | None = None,
        context: dict[str, Any] | None = None,
    ) -> FallbackResult:
        """Execute primary function with retry and fallback on failure.

        Args:
            component: Component identifier
            primary_func: Primary async function to execute
            fallback_func: Fallback function (uses registered handler if None)
            context: Additional context for execution

        Returns:
            FallbackResult with execution details
        """
        start_time = datetime.now()
        ctx = FallbackContext(
            component=component,
            operation=primary_func.__name__,
            metadata=context or {},
        )

        # Step 1: Try with retry manager (if available)
        if self._retry_manager:
            try:
                _logger.debug(
                    "orchestration_retry_attempt",
                    component=component,
                )
                retry_result = await self._retry_manager.execute_with_retry(
                    component=component,
                    primary_func=primary_func,
                    context=context,
                )

                if retry_result.success:
                    latency = (datetime.now() - start_time).total_seconds()

                    # Record success metrics
                    if self._metrics_collector:
                        self._metrics_collector.record_fallback(
                            component=component,
                            success=True,
                            fallback_used=False,
                            latency=latency,
                        )

                    # Update component status
                    async with self._get_lock():
                        self._component_status[component] = ComponentStatus.HEALTHY

                    return FallbackResult(
                        success=True,
                        result=retry_result.result,
                        fallback_used=False,
                        component=component,
                        latency_seconds=latency,
                    )
                else:
                    _logger.warning(
                        "orchestration_retry_exhausted",
                        component=component,
                        attempts_made=retry_result.attempts_made,
                        error=retry_result.error,
                    )
                    ctx.original_error = retry_result.error

            except Exception as exc:
                _logger.error(
                    "orchestration_retry_error",
                    component=component,
                    error=str(exc),
                )
                ctx.original_error = str(exc)
        else:
            # No retry manager - try primary directly
            try:
                result = await primary_func()
                latency = (datetime.now() - start_time).total_seconds()

                # Record success metrics
                if self._metrics_collector:
                    self._metrics_collector.record_fallback(
                        component=component,
                        success=True,
                        fallback_used=False,
                        latency=latency,
                    )

                # Update component status
                async with self._get_lock():
                    self._component_status[component] = ComponentStatus.HEALTHY

                return FallbackResult(
                    success=True,
                    result=result,
                    fallback_used=False,
                    component=component,
                    latency_seconds=latency,
                )

            except Exception as exc:
                _logger.warning(
                    "orchestration_primary_execution_failed",
                    component=component,
                    error=str(exc),
                )
                ctx.original_error = str(exc)

        # Step 2: Execute fallback if primary/retry failed
        handler = fallback_func or self._fallback_handlers.get(component)

        if handler is None:
            _logger.error(
                "orchestration_no_fallback_handler",
                component=component,
                error=str(ctx.original_error),
            )

            latency = (datetime.now() - start_time).total_seconds()

            if self._metrics_collector:
                self._metrics_collector.record_fallback(
                    component=component,
                    success=False,
                    fallback_used=False,
                    latency=latency,
                )

            return FallbackResult(
                success=False,
                result=None,
                fallback_used=False,
                component=component,
                latency_seconds=latency,
                error=str(ctx.original_error),
            )

        try:
            result = await handler(ctx)

            latency = (datetime.now() - start_time).total_seconds()

            # Record fallback metrics
            if self._metrics_collector:
                self._metrics_collector.record_fallback(
                    component=component,
                    success=True,
                    fallback_used=True,
                    latency=latency,
                )

            # Update component status
            async with self._get_lock():
                self._component_status[component] = ComponentStatus.FALLBACK_ACTIVE

            _logger.info(
                "orchestration_fallback_success",
                component=component,
                latency=latency,
            )

            return FallbackResult(
                success=True,
                result=result,
                fallback_used=True,
                component=component,
                latency_seconds=latency,
            )

        except Exception as fallback_exc:
            latency = (datetime.now() - start_time).total_seconds()

            if self._metrics_collector:
                self._metrics_collector.record_fallback(
                    component=component,
                    success=False,
                    fallback_used=True,
                    latency=latency,
                )

            _logger.error(
                "orchestration_fallback_failed",
                component=component,
                original_error=str(ctx.original_error),
                fallback_error=str(fallback_exc),
            )

            return FallbackResult(
                success=False,
                result=None,
                fallback_used=True,
                component=component,
                latency_seconds=latency,
                error=str(fallback_exc),
            )

    def get_component_status(self, component: str) -> ComponentStatus:
        """Get the current status of a component.

        Args:
            component: Component identifier

        Returns:
            ComponentStatus enum value
        """
        return self._component_status.get(component, ComponentStatus.HEALTHY)

    def list_components(self) -> list[str]:
        """List all registered components.

        Returns:
            List of component identifiers
        """
        return list(self._fallback_handlers.keys())

    def reset_component_status(self, component: str) -> None:
        """Reset component status to HEALTHY.

        Args:
            component: Component identifier
        """
        self._component_status[component] = ComponentStatus.HEALTHY
        _logger.info("orchestration_component_status_reset", component=component)


# Global instance
_orchestration_fallback_manager: OrchestrationFallbackManager | None = None


def get_orchestration_fallback_manager() -> OrchestrationFallbackManager:
    """Get or create the global orchestration fallback manager instance."""
    global _orchestration_fallback_manager
    if _orchestration_fallback_manager is None:
        _orchestration_fallback_manager = OrchestrationFallbackManager()

        # Integrate with retry manager
        from mindflow_backend.infra.resilience.orchestration_retry import (
            get_orchestration_retry_manager,
        )

        _orchestration_fallback_manager.set_retry_manager(get_orchestration_retry_manager())

        _logger.info("orchestration_fallback_manager_initialized")
    return _orchestration_fallback_manager
