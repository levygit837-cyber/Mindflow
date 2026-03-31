"""Lifecycle management interfaces.

Provides standardized interfaces for component lifecycle management,
including initialization, shutdown, health checks, and status monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class ComponentStatus(Enum):
    """Status of a component in its lifecycle."""
    
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    healthy: bool
    status: ComponentStatus
    message: str
    timestamp: datetime
    details: dict[str, Any] | None = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class LifecycleMetrics:
    """Metrics for component lifecycle operations."""
    
    startup_time: float | None = None  # seconds
    shutdown_time: float | None = None  # seconds
    uptime: float | None = None  # seconds
    restart_count: int = 0
    last_error: Exception | None = None
    last_error_time: datetime | None = None


@runtime_checkable
class LifecycleInterface(Protocol):
    """Interface for component lifecycle management.
    
    Provides standardized methods for initializing components,
    managing their lifecycle, handling shutdown gracefully,
    and monitoring health status.
    """
    
    async def initialize(self) -> None:
        """Initialize the component and its resources.
        
        This method should be called before the component is used
        to set up any necessary resources, connections, or state.
        
        Raises:
            Exception: If initialization fails
        """
        ...
    
    async def shutdown(self) -> None:
        """Shutdown the component and cleanup resources.
        
        This method should be called when the component is no longer
        needed to gracefully cleanup resources and save state.
        
        Raises:
            Exception: If shutdown fails
        """
        ...
    
    def is_healthy(self) -> bool:
        """Check if the component is healthy.
        
        Returns:
            True if the component is operating normally, False otherwise
        """
        ...
    
    async def health_check(self) -> HealthCheckResult:
        """Perform detailed health check.
        
        Returns:
            Detailed health check result with status and metrics
        """
        ...
    
    def get_status(self) -> ComponentStatus:
        """Get the current status of the component.
        
        Returns:
            Current component status
        """
        ...
    
    def get_lifecycle_metrics(self) -> LifecycleMetrics:
        """Get lifecycle metrics for monitoring.
        
        Returns:
            Metrics about component lifecycle operations
        """
        ...
    
    async def restart(self) -> None:
        """Restart the component.
        
        This method should shutdown and reinitialize the component
        to recover from errors or apply configuration changes.
        
        Raises:
            Exception: If restart fails
        """
        ...
    
    def set_status(self, status: ComponentStatus) -> None:
        """Set the component status.
        
        Args:
            status: New status to set
        """
        ...
    
    async def maintenance_mode(self, enable: bool) -> None:
        """Enable or disable maintenance mode.
        
        Args:
            enable: True to enable maintenance mode, False to disable
            
        Raises:
            Exception: If maintenance mode change fails
        """
        ...


@runtime_checkable
class AsyncLifecycleInterface(LifecycleInterface, Protocol):
    """Extended lifecycle interface with additional async operations.
    
    Provides additional async-specific lifecycle operations for components
    that require more sophisticated async lifecycle management.
    """
    
    async def warm_up(self) -> None:
        """Warm up the component before it starts handling requests.
        
        This method is called after initialization but before the component
        is marked as ready to handle requests. Useful for pre-loading data,
        establishing connection pools, etc.
        
        Raises:
            Exception: If warm up fails
        """
        ...
    
    async def cool_down(self) -> None:
        """Cool down the component before shutdown.
        
        This method is called before shutdown to gracefully finish
        in-progress operations and prepare for shutdown.
        
        Raises:
            Exception: If cool down fails
        """
        ...
    
    async def graceful_shutdown(self, timeout: float | None = None) -> bool:
        """Attempt graceful shutdown with timeout.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
            
        Returns:
            True if graceful shutdown succeeded, False if timeout exceeded
        """
        ...
    
    def can_handle_requests(self) -> bool:
        """Check if component can handle new requests.
        
        Returns:
            True if component is ready to handle requests
        """
        ...


@runtime_checkable
class ManagedLifecycleInterface(AsyncLifecycleInterface, Protocol):
    """Interface for components with managed lifecycle.
    
    Used for components that are managed by an external lifecycle manager
    like Kubernetes, Docker, or a custom orchestration system.
    """
    
    async def readiness_check(self) -> bool:
        """Check if component is ready to serve requests.
        
        This is used by orchestration systems to determine if the component
        is ready to receive traffic.
        
        Returns:
            True if ready, False otherwise
        """
        ...
    
    async def liveness_check(self) -> bool:
        """Check if component is still alive.
        
        This is used by orchestration systems to determine if the component
        needs to be restarted.
        
        Returns:
            True if alive, False otherwise
        """
        ...
    
    async def startup_probe(self) -> bool:
        """Probe to check if component has successfully started.
        
        Returns:
            True if startup is complete, False otherwise
        """
        ...
    
    def get_startup_timeout(self) -> float:
        """Get the startup timeout for this component.
        
        Returns:
            Maximum time to wait for startup in seconds
        """
        ...
    
    def get_shutdown_timeout(self) -> float:
        """Get the shutdown timeout for this component.
        
        Returns:
            Maximum time to wait for shutdown in seconds
        """
        ...
