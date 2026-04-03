"""Remote configuration for circuit breakers via feature flags.

Integrates with GrowthBook/LaunchDarkly for dynamic circuit breaker
configuration without code deployments.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class FeatureFlagProvider(str, Enum):
    """Supported feature flag providers."""
    GROWTHBOOK = "growthbook"
    LAUNCHDARKLY = "launchdarkly"
    LOCAL = "local"


@dataclass
class CircuitBreakerRemoteConfig:
    """Remote configuration for circuit breaker.

    Can be updated via feature flags without code deployment.
    Inspired by Claude Code's GrowthBook integration.
    """

    service_name: str
    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0
    max_half_open_calls: int = 3
    fallback_enabled: bool = True

    # Enhanced settings
    adaptive_threshold_type: str = "fixed"
    min_failure_threshold: int = 3
    max_failure_threshold: int = 20
    enable_dynamic_config: bool = True
    auto_tune_thresholds: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "service_name": self.service_name,
            "enabled": self.enabled,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "max_half_open_calls": self.max_half_open_calls,
            "fallback_enabled": self.fallback_enabled,
            "adaptive_threshold_type": self.adaptive_threshold_type,
            "min_failure_threshold": self.min_failure_threshold,
            "max_failure_threshold": self.max_failure_threshold,
            "enable_dynamic_config": self.enable_dynamic_config,
            "auto_tune_thresholds": self.auto_tune_thresholds,
        }


class RemoteCircuitBreakerConfig:
    """Manages remote configuration for circuit breakers.

    Integrates with feature flag providers to dynamically update
    circuit breaker settings without code deployments.
    """

    def __init__(
        self,
        provider: FeatureFlagProvider = FeatureFlagProvider.LOCAL,
        refresh_interval: float = 60.0,
    ):
        self.provider = provider
        self.refresh_interval = refresh_interval
        self._configs: dict[str, CircuitBreakerRemoteConfig] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        self._refresh_task: asyncio.Task | None = None
        self._running = False

        _logger.info(
            "remote_config_initialized",
            provider=provider.value,
            refresh_interval=refresh_interval,
        )

    def get_config(self, service_name: str) -> CircuitBreakerRemoteConfig:
        """Get remote configuration for a service.

        Args:
            service_name: Name of the service

        Returns:
            CircuitBreakerRemoteConfig for the service
        """
        if service_name not in self._configs:
            self._configs[service_name] = CircuitBreakerRemoteConfig(
                service_name=service_name
            )
        return self._configs[service_name]

    def update_config(
        self,
        service_name: str,
        config_updates: dict[str, Any],
    ) -> None:
        """Update configuration for a service.

        Args:
            service_name: Name of the service
            config_updates: Dictionary of config updates
        """
        current = self.get_config(service_name)

        # Update fields
        for key, value in config_updates.items():
            if hasattr(current, key):
                setattr(current, key, value)

        _logger.info(
            "remote_config_updated",
            service_name=service_name,
            updates=config_updates,
        )

        # Notify callbacks
        self._notify_callbacks(service_name, current)

    def register_callback(
        self,
        service_name: str,
        callback: Callable[[CircuitBreakerRemoteConfig], None],
    ) -> None:
        """Register a callback for config changes.

        Args:
            service_name: Name of the service
            callback: Callback function to call on config change
        """
        if service_name not in self._callbacks:
            self._callbacks[service_name] = []
        self._callbacks[service_name].append(callback)

    def _notify_callbacks(
        self,
        service_name: str,
        config: CircuitBreakerRemoteConfig,
    ) -> None:
        """Notify all registered callbacks for a service."""
        if service_name in self._callbacks:
            for callback in self._callbacks[service_name]:
                try:
                    callback(config)
                except Exception as e:
                    _logger.error(
                        "remote_config_callback_error",
                        service_name=service_name,
                        error=str(e),
                    )

    async def start_auto_refresh(self) -> None:
        """Start automatic config refresh."""
        if self._running:
            return

        self._running = True
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        _logger.info("remote_config_auto_refresh_started")

    async def stop_auto_refresh(self) -> None:
        """Stop automatic config refresh."""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        _logger.info("remote_config_auto_refresh_stopped")

    async def _refresh_loop(self) -> None:
        """Background loop for config refresh."""
        while self._running:
            try:
                await asyncio.sleep(self.refresh_interval)
                await self._refresh_configs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("remote_config_refresh_error", error=str(e))

    async def _refresh_configs(self) -> None:
        """Refresh configurations from feature flag provider."""
        # Implementation depends on provider
        if self.provider == FeatureFlagProvider.GROWTHBOOK:
            await self._refresh_growthbook()
        elif self.provider == FeatureFlagProvider.LAUNCHDARKLY:
            await self._refresh_launchdarkly()
        # LOCAL provider doesn't need refresh

    async def _refresh_growthbook(self) -> None:
        """Refresh configs from GrowthBook."""
        # TODO: Implement GrowthBook integration
        _logger.debug("growthbook_refresh_skipped", reason="not_implemented")

    async def _refresh_launchdarkly(self) -> None:
        """Refresh configs from LaunchDarkly."""
        # TODO: Implement LaunchDarkly integration
        _logger.debug("launchdarkly_refresh_skipped", reason="not_implemented")

    def get_all_configs(self) -> dict[str, dict[str, Any]]:
        """Get all configurations.

        Returns:
            Dictionary of service_name -> config_dict
        """
        return {
            name: config.to_dict()
            for name, config in self._configs.items()
        }