"""Comprehensive health check system for OmniMind infrastructure.

Provides unified health monitoring across all system components
including database, cache, external APIs, and system resources.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from mindflow_backend.infra.database.health import get_health_checker
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """System component types for health checking."""
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    SYSTEM_RESOURCES = "system_resources"
    APPLICATION = "application"
    CUSTOM = "custom"


@dataclass
class HealthCheckResult:
    """Result of a health check for a component."""
    component: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    response_time_ms: float = 0.0
    error: Exception | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "component": self.component,
            "component_type": self.component_type.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "error": str(self.error) if self.error else None,
        }


@dataclass
class SystemHealthSummary:
    """Overall system health summary."""
    status: HealthStatus
    total_components: int
    healthy_components: int
    degraded_components: int
    unhealthy_components: int
    unknown_components: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    component_results: list[HealthCheckResult] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "status": self.status.value,
            "total_components": self.total_components,
            "healthy_components": self.healthy_components,
            "degraded_components": self.degraded_components,
            "unhealthy_components": self.unhealthy_components,
            "unknown_components": self.unknown_components,
            "timestamp": self.timestamp.isoformat(),
            "components": [result.to_dict() for result in self.component_results],
        }


class HealthChecker(ABC):
    """Abstract base class for component health checkers."""
    
    def __init__(self, component: str, component_type: ComponentType):
        """Initialize health checker.
        
        Args:
            component: Component name
            component_type: Type of component
        """
        self.component = component
        self.component_type = component_type
        self.last_check: HealthCheckResult | None = None
        self.check_count = 0
        self.failure_count = 0
        
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform health check for the component.
        
        Returns:
            HealthCheckResult with current health status.
        """
        pass
        
    def get_statistics(self) -> dict[str, Any]:
        """Get health check statistics.
        
        Returns:
            Dictionary with check statistics.
        """
        return {
            "component": self.component,
            "component_type": self.component_type.value,
            "check_count": self.check_count,
            "failure_count": self.failure_count,
            "success_rate": (self.check_count - self.failure_count) / max(self.check_count, 1),
            "last_check": self.last_check.timestamp.isoformat() if self.last_check else None,
            "last_status": self.last_check.status.value if self.last_check else None,
        }


class DatabaseHealthChecker(HealthChecker):
    """Health checker for database components."""
    
    def __init__(self, component: str = "postgresql"):
        """Initialize database health checker.
        
        Args:
            component: Database component name
        """
        super().__init__(component, ComponentType.DATABASE)
        self._db_health_checker = get_health_checker()
        
    async def check_health(self) -> HealthCheckResult:
        """Check database health."""
        start_time = datetime.now(UTC)
        
        try:
            health_data = self._normalize_health_data(
                await self._db_health_checker.check_health()
            )
            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            # Determine status based on health data
            if health_data["status"] == "healthy" and health_data["latency_ms"] < 100:
                status = HealthStatus.HEALTHY
                message = "Database is healthy and responsive"
            elif health_data["status"] == "healthy":
                status = HealthStatus.DEGRADED
                message = f"Database is healthy but slow ({health_data['latency_ms']:.1f}ms)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Database is unhealthy: {health_data.get('error', 'Unknown error')}"
                
            result = HealthCheckResult(
                component=self.component,
                component_type=self.component_type,
                status=status,
                message=message,
                details=health_data,
                response_time_ms=response_time,
            )
            
            self.last_check = result
            self.check_count += 1
            
            if status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
                self.failure_count += 1
                
            return result
            
        except Exception as e:
            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                component=self.component,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}",
                response_time_ms=response_time,
                error=e,
            )
            
            self.last_check = result
            self.check_count += 1
            self.failure_count += 1
            
            return result

    @staticmethod
    def _normalize_health_data(raw_health_data: Any) -> dict[str, Any]:
        if isinstance(raw_health_data, dict):
            return raw_health_data

        health_data = dict(getattr(raw_health_data, "details", {}) or {})
        health_data.setdefault("status", getattr(raw_health_data, "status", "unknown"))
        health_data.setdefault("latency_ms", getattr(raw_health_data, "latency_ms", None))

        error = getattr(raw_health_data, "error", None)
        if error is not None:
            health_data.setdefault("error", str(error))

        timestamp = getattr(raw_health_data, "timestamp", None)
        if timestamp is not None:
            health_data.setdefault(
                "timestamp",
                timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp,
            )

        return health_data


class CacheHealthChecker(HealthChecker):
    """Health checker for cache components."""
    
    def __init__(self, component: str = "redis"):
        """Initialize cache health checker.
        
        Args:
            component: Cache component name
        """
        super().__init__(component, ComponentType.CACHE)
        
    async def check_health(self) -> HealthCheckResult:
        """Check cache health."""
        start_time = datetime.now(UTC)
        
        try:
            # TODO: Implement actual Redis health check
            # For now, simulate health check
            await asyncio.sleep(0.01)  # Simulate network latency
            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            if response_time < 50:
                status = HealthStatus.HEALTHY
                message = "Cache is healthy and responsive"
            elif response_time < 200:
                status = HealthStatus.DEGRADED
                message = f"Cache is responsive but slow ({response_time:.1f}ms)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Cache is too slow ({response_time:.1f}ms)"
                
            result = HealthCheckResult(
                component=self.component,
                component_type=self.component_type,
                status=status,
                message=message,
                details={
                    "response_time_ms": response_time,
                    "connection_status": "connected",
                },
                response_time_ms=response_time,
            )
            
            self.last_check = result
            self.check_count += 1
            
            if status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
                self.failure_count += 1
                
            return result
            
        except Exception as e:
            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                component=self.component,
                component_type=self.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Cache health check failed: {str(e)}",
                response_time_ms=response_time,
                error=e,
            )
            
            self.last_check = result
            self.check_count += 1
            self.failure_count += 1
            
            return result


class SystemResourceHealthChecker(HealthChecker):
    """Health checker for system resources."""
    
    def __init__(self, component: str = "system_resources"):
        """Initialize system resource health checker.
        
        Args:
            component: Component name
        """
        super().__init__(component, ComponentType.SYSTEM_RESOURCES)
        
    async def check_health(self) -> HealthCheckResult:
        """Check system resource health."""
        start_time = datetime.now(UTC)
        
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            # Determine overall status
            issues = []
            
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
                
            if memory.percent > 90:
                issues.append(f"High memory usage: {memory.percent:.1f}%")
                
            if disk.percent > 90:
                issues.append(f"High disk usage: {disk.percent:.1f}%")
                
            if not issues:
                status = HealthStatus.HEALTHY
                message = "System resources are healthy"
            elif len(issues) == 1:
                status = HealthStatus.DEGRADED
                message = issues[0]
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Multiple resource issues: {', '.join(issues)}"
                
            result = HealthCheckResult(
                component=self.component,
                component_type=self.component_type,
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_free_gb": disk.free / (1024**3),
                },
                response_time_ms=response_time,
            )
            
            self.last_check = result
            self.check_count += 1
            
            if status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
                self.failure_count += 1
                
            return result
            
        except Exception as e:
            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                component=self.component,
                component_type=self.component_type,
                status=HealthStatus.UNKNOWN,
                message=f"System resource check failed: {str(e)}",
                response_time_ms=response_time,
                error=e,
            )
            
            self.last_check = result
            self.check_count += 1
            self.failure_count += 1
            
            return result


class HealthCheckManager:
    """Central manager for all system health checks.
    
    Provides:
    - Unified health check orchestration
    - Component registration and management
    - Health status aggregation
    - Continuous monitoring
    - Alerting integration
    """
    
    def __init__(self):
        """Initialize health check manager."""
        self._checkers: dict[str, HealthChecker] = {}
        self._monitoring_task: asyncio.Task | None = None
        self._is_monitoring = False
        self._last_system_check: SystemHealthSummary | None = None
        
        # Register default health checkers
        self._register_default_checkers()
        
    def _register_default_checkers(self) -> None:
        """Register default health checkers for core components."""
        self.register_checker(DatabaseHealthChecker())
        self.register_checker(CacheHealthChecker())
        self.register_checker(SystemResourceHealthChecker())
        
    def register_checker(self, checker: HealthChecker) -> None:
        """Register a health checker.
        
        Args:
            checker: Health checker instance to register
        """
        self._checkers[checker.component] = checker
        _logger.info(
            "health_checker_registered",
            component=checker.component,
            component_type=checker.component_type.value,
        )
        
    def unregister_checker(self, component: str) -> None:
        """Unregister a health checker.
        
        Args:
            component: Component name to unregister
        """
        if component in self._checkers:
            del self._checkers[component]
            _logger.info("health_checker_unregistered", component=component)
            
    async def check_component_health(self, component: str) -> HealthCheckResult | None:
        """Check health for a specific component.
        
        Args:
            component: Component name to check
            
        Returns:
            Health check result or None if component not found.
        """
        checker = self._checkers.get(component)
        if not checker:
            _logger.warning("health_checker_not_found", component=component)
            return None
            
        try:
            return await checker.check_health()
        except Exception as e:
            _logger.error(
                "component_health_check_failed",
                component=component,
                error=str(e),
            )
            return HealthCheckResult(
                component=component,
                component_type=checker.component_type,
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                error=e,
            )
            
    async def check_system_health(self) -> SystemHealthSummary:
        """Check health for all registered components.
        
        Returns:
            System health summary with all component results.
        """
        start_time = datetime.now(UTC)
        
        # Run all health checks concurrently
        tasks = [
            self.check_component_health(component)
            for component in self._checkers.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        component_results = []
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        unknown_count = 0
        
        for i, result in enumerate(results):
            component = list(self._checkers.keys())[i]
            
            if isinstance(result, Exception):
                # Handle exceptions in health checks
                error_result = HealthCheckResult(
                    component=component,
                    component_type=ComponentType.CUSTOM,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check error: {str(result)}",
                    error=result,
                )
                component_results.append(error_result)
                unknown_count += 1
            elif result is not None:
                component_results.append(result)
                
                if result.status == HealthStatus.HEALTHY:
                    healthy_count += 1
                elif result.status == HealthStatus.DEGRADED:
                    degraded_count += 1
                elif result.status == HealthStatus.UNHEALTHY:
                    unhealthy_count += 1
                else:
                    unknown_count += 1
            else:
                # Component not found
                unknown_count += 1
                
        total_components = len(component_results)
        
        # Determine overall system status
        if unhealthy_count > 0:
            system_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            system_status = HealthStatus.DEGRADED
        elif healthy_count == total_components:
            system_status = HealthStatus.HEALTHY
        else:
            system_status = HealthStatus.UNKNOWN
            
        summary = SystemHealthSummary(
            status=system_status,
            total_components=total_components,
            healthy_components=healthy_count,
            degraded_components=degraded_count,
            unhealthy_components=unhealthy_count,
            unknown_components=unknown_count,
            component_results=component_results,
        )
        
        self._last_system_check = summary
        
        _logger.info(
            "system_health_check_completed",
            status=system_status.value,
            total=total_components,
            healthy=healthy_count,
            degraded=degraded_count,
            unhealthy=unhealthy_count,
            unknown=unknown_count,
            duration_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
        )
        
        return summary
        
    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start continuous health monitoring.
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self._is_monitoring:
            return
            
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
        
        _logger.info(
            "health_monitoring_started",
            interval=interval_seconds,
            components=len(self._checkers),
        )
        
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self._is_monitoring:
            return
            
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("health_monitoring_stopped")
        
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop for continuous health checks.
        
        Args:
            interval_seconds: Interval between health checks
        """
        while self._is_monitoring:
            try:
                await self.check_system_health()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("health_monitoring_loop_error", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry
                
    def get_component_statistics(self, component: str) -> dict[str, Any] | None:
        """Get statistics for a specific component.
        
        Args:
            component: Component name
            
        Returns:
            Component statistics or None if not found.
        """
        checker = self._checkers.get(component)
        return checker.get_statistics() if checker else None
        
    def get_all_statistics(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all components.
        
        Returns:
            Dictionary with all component statistics.
        """
        return {
            component: checker.get_statistics()
            for component, checker in self._checkers.items()
        }
        
    def get_last_system_check(self) -> SystemHealthSummary | None:
        """Get the last system health check result.
        
        Returns:
            Last system health summary or None if no checks performed.
        """
        return self._last_system_check


# Global health check manager instance
_health_manager: HealthCheckManager | None = None


def get_health_manager() -> HealthCheckManager:
    """Get global health check manager instance."""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    return _health_manager
