"""Orchestration Retry Manager - Configurable retry logic before fallback.

Provides persistent retry mechanisms with customizable backoff strategies
for orchestration components before triggering fallback handlers.

Features:
- Configurable retry counts
- Customizable backoff intervals
- Per-component retry configuration
- Integration with OrchestrationFallbackManager
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class OrchestrationRetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_retries: int = Field(default=10, description="Maximum number of retries")
    initial_backoff_seconds: float = Field(default=5.0, description="Initial backoff in seconds")
    backoff_multiplier: float = Field(default=1.0, description="Multiplier for backoff after initial retries")
    backoff_step_seconds: float = Field(default=10.0, description="Step increase for backoff after initial retries")
    initial_retry_count: int = Field(default=5, description="Number of retries with initial backoff")

    def get_backoff_for_attempt(self, attempt: int) -> float:
        """Get backoff delay for a specific retry attempt.

        Args:
            attempt: Retry attempt number (1-indexed)

        Returns:
            Backoff delay in seconds
        """
        if attempt <= self.initial_retry_count:
            return self.initial_backoff_seconds
        else:
            # Calculate backoff: initial_backoff + (attempt - initial_retry_count) * backoff_step
            step = attempt - self.initial_retry_count
            return self.initial_backoff_seconds + (step * self.backoff_step_seconds)


class RetryContext(BaseModel):
    """Context information for a retry operation."""

    component: str
    attempt: int
    max_retries: int
    original_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    start_time: datetime = Field(default_factory=datetime.now)

    model_config = {"arbitrary_types_allowed": True}


class RetryResult(BaseModel):
    """Result of a retry operation."""

    success: bool
    result: Any = None
    error: str | None = None
    attempts_made: int = 0
    total_duration_seconds: float = 0.0


class OrchestrationRetryManager:
    """Manages retry logic for orchestration components.

    Provides configurable retry mechanisms with custom backoff strategies
    before triggering fallback handlers.
    """

    def __init__(self):
        self.settings = get_settings()
        self._retry_configs: dict[str, OrchestrationRetryConfig] = {}

    def register_retry_config(self, component: str, config: OrchestrationRetryConfig) -> None:
        """Register retry configuration for a component.

        Args:
            component: Component identifier
            config: Retry configuration
        """
        self._retry_configs[component] = config
        _logger.debug(
            "retry_config_registered",
            component=component,
            max_retries=config.max_retries,
            initial_backoff=config.initial_backoff_seconds,
        )

    def get_retry_config(self, component: str) -> OrchestrationRetryConfig:
        """Get retry configuration for a component.

        Args:
            component: Component identifier

        Returns:
            Retry configuration (default if not registered)
        """
        if component in self._retry_configs:
            return self._retry_configs[component]

        # Return default configuration
        return OrchestrationRetryConfig()

    async def execute_with_retry(
        self,
        component: str,
        primary_func: Callable[[], Any],
        context: dict[str, Any] | None = None,
    ) -> RetryResult:
        """Execute function with retry logic before fallback.

        Args:
            component: Component identifier
            primary_func: Primary function to execute
            context: Additional context metadata

        Returns:
            RetryResult with success status and result/error
        """
        config = self.get_retry_config(component)
        retry_context = RetryContext(
            component=component,
            attempt=0,
            max_retries=config.max_retries,
            metadata=context or {},
        )

        start_time = datetime.now()
        last_error: str | None = None

        for attempt in range(1, config.max_retries + 1):
            retry_context.attempt = attempt

            try:
                _logger.debug(
                    "retry_attempt",
                    component=component,
                    attempt=attempt,
                    max_retries=config.max_retries,
                )

                result = await primary_func()

                # Success - return result
                duration = (datetime.now() - start_time).total_seconds()
                _logger.info(
                    "retry_success",
                    component=component,
                    attempt=attempt,
                    duration_seconds=duration,
                )

                return RetryResult(
                    success=True,
                    result=result,
                    attempts_made=attempt,
                    total_duration_seconds=duration,
                )

            except Exception as exc:
                last_error = str(exc)
                _logger.warning(
                    "retry_failed",
                    component=component,
                    attempt=attempt,
                    error=str(exc),
                )

                # If this was the last attempt, break
                if attempt >= config.max_retries:
                    break

                # Calculate backoff and wait
                backoff = config.get_backoff_for_attempt(attempt)
                _logger.debug(
                    "retry_backoff",
                    component=component,
                    attempt=attempt,
                    backoff_seconds=backoff,
                )
                await asyncio.sleep(backoff)

        # All retries exhausted
        duration = (datetime.now() - start_time).total_seconds()
        _logger.error(
            "retry_exhausted",
            component=component,
            attempts_made=config.max_retries,
            total_duration_seconds=duration,
            error=str(last_error),
        )

        return RetryResult(
            success=False,
            error=str(last_error) if last_error else "Unknown error",
            attempts_made=config.max_retries,
            total_duration_seconds=duration,
        )


# Global retry manager instance
_retry_manager: OrchestrationRetryManager | None = None


def get_orchestration_retry_manager() -> OrchestrationRetryManager:
    """Get or create the global orchestration retry manager instance."""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = OrchestrationRetryManager()
        _register_default_retry_configs()
    return _retry_manager


def _register_default_retry_configs() -> None:
    """Register default retry configurations for orchestration components."""
    manager = get_orchestration_retry_manager()

    # TeamOrchestrator: 10 retries, 5s for first 5, then 20s, 30s, 40s, 50s, 60s
    manager.register_retry_config(
        "team_orchestrator",
        OrchestrationRetryConfig(
            max_retries=10,
            initial_backoff_seconds=5.0,
            initial_retry_count=5,
            backoff_step_seconds=10.0,
        ),
    )

    # IntelligentRouter: 10 retries, 5s for first 5, then 20s, 30s, 40s, 50s, 60s
    manager.register_retry_config(
        "intelligent_router",
        OrchestrationRetryConfig(
            max_retries=10,
            initial_backoff_seconds=5.0,
            initial_retry_count=5,
            backoff_step_seconds=10.0,
        ),
    )

    # DelegationEngine: 10 retries, 5s for first 5, then 20s, 30s, 40s, 50s, 60s
    manager.register_retry_config(
        "delegation_engine",
        OrchestrationRetryConfig(
            max_retries=10,
            initial_backoff_seconds=5.0,
            initial_retry_count=5,
            backoff_step_seconds=10.0,
        ),
    )

    # CommunicationBus: 10 retries, 5s for first 5, then 20s, 30s, 40s, 50s, 60s
    manager.register_retry_config(
        "communication_bus_send",
        OrchestrationRetryConfig(
            max_retries=10,
            initial_backoff_seconds=5.0,
            initial_retry_count=5,
            backoff_step_seconds=10.0,
        ),
    )

    manager.register_retry_config(
        "communication_bus_broadcast",
        OrchestrationRetryConfig(
            max_retries=10,
            initial_backoff_seconds=5.0,
            initial_retry_count=5,
            backoff_step_seconds=10.0,
        ),
    )
