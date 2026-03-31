"""Advanced health checking for gRPC services.

Provides comprehensive health monitoring including service health,
dependency health, system health, and custom health checks.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Comprehensive health report."""
    status: HealthStatus
    checks: list[HealthCheck]
    uptime_seconds: float
    version: str
    timestamp: float
    dependencies: dict[str, HealthStatus] = field(default_factory=dict)


class HealthChecker:
    """Base class for health check implementations."""
    
    def __init__(self, name: str, timeout_seconds: float = 10.0):
        self.name = name
        self.timeout_seconds = timeout_seconds
    
    async def check(self) -> HealthCheck:
        """Perform health check."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(self._check_implementation(), timeout=self.timeout_seconds)
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheck(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=result.get('message', 'OK'),
                duration_ms=duration_ms,
                timestamp=time.time(),
                details=result.get('details', {})
            )
            
        except TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                duration_ms=duration_ms,
                timestamp=time.time()
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(exc)}",
                duration_ms=duration_ms,
                timestamp=time.time(),
                details={'error': str(exc)}
            )
    
    async def _check_implementation(self) -> dict[str, Any]:
        """Implementation-specific health check logic."""
        raise NotImplementedError


class GrpcServiceHealthChecker(HealthChecker):
    """Health checker for gRPC service availability."""
    
    def __init__(self, host: str = "localhost", port: int = 50051, **kwargs):
        super().__init__("grpc_service", **kwargs)
        self.host = host
        self.port = port
    
    async def _check_implementation(self) -> dict[str, Any]:
        """Check gRPC service health."""
        import grpc
        
        try:
            # Try to connect to gRPC server
            channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            grpc.channel_ready_future(channel).result(timeout=self.timeout_seconds)
            
            return {
                'message': f'gRPC service reachable at {self.host}:{self.port}',
                'details': {
                    'host': self.host,
                    'port': self.port,
                    'protocol': 'grpc'
                }
            }
        finally:
            if 'channel' in locals():
                channel.close()


class DatabaseHealthChecker(HealthChecker):
    """Health checker for database connectivity."""
    
    def __init__(self, database_url: str, **kwargs):
        super().__init__("database", **kwargs)
        self.database_url = database_url
    
    async def _check_implementation(self) -> dict[str, Any]:
        """Check database connectivity."""
        try:
            from mindflow_backend.storage import engine
            
            # Try to execute a simple query
            with engine.connect() as conn:
                result = conn.execute("SELECT 1").fetchone()
            
            return {
                'message': 'Database connection successful',
                'details': {
                    'database_url': self.database_url.split('@')[1] if '@' in self.database_url else 'unknown',
                    'test_query': 'SELECT 1'
                }
            }
        except Exception as exc:
            raise Exception(f"Database connection failed: {str(exc)}")


class VectorStoreHealthChecker(HealthChecker):
    """Health checker for vector store connectivity."""
    
    def __init__(self, vector_db_url: str, **kwargs):
        super().__init__("vector_store", **kwargs)
        self.vector_db_url = vector_db_url
    
    async def _check_implementation(self) -> dict[str, Any]:
        """Check vector store connectivity."""
        try:
            # Try to connect to vector store
            # This is a placeholder - implement based on your vector store
            import requests
            
            response = requests.get(f"{self.vector_db_url}/health", timeout=self.timeout_seconds)
            response.raise_for_status()
            
            return {
                'message': 'Vector store connection successful',
                'details': {
                    'url': self.vector_db_url,
                    'status_code': response.status_code
                }
            }
        except Exception as exc:
            raise Exception(f"Vector store connection failed: {str(exc)}")


class SystemHealthChecker(HealthChecker):
    """Health checker for system resources."""
    
    def __init__(self, cpu_threshold: float = 80.0, memory_threshold: float = 80.0, **kwargs):
        super().__init__("system", **kwargs)
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
    
    async def _check_implementation(self) -> dict[str, Any]:
        """Check system resource health."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Determine overall status
            issues = []
            if cpu_percent > self.cpu_threshold:
                issues.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            if memory_percent > self.memory_threshold:
                issues.append(f"Memory usage high: {memory_percent:.1f}%")
            
            status = HealthStatus.HEALTHY
            message = "System resources OK"
            
            if issues:
                if len(issues) == 1 and "high" in issues[0]:
                    status = HealthStatus.DEGRADED
                    message = issues[0]
                else:
                    status = HealthStatus.UNHEALTHY
                    message = "; ".join(issues)
            
            return {
                'message': message,
                'details': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'cpu_threshold': self.cpu_threshold,
                    'memory_threshold': self.memory_threshold,
                    'issues': issues
                }
            }
            
        except ImportError:
            return {
                'message': 'psutil not available, cannot check system resources',
                'details': {'error': 'psutil not installed'}
            }


class CustomHealthChecker(HealthChecker):
    """Custom health checker for application-specific logic."""
    
    def __init__(self, check_function: callable, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self.check_function = check_function
    
    async def _check_implementation(self) -> dict[str, Any]:
        """Execute custom health check function."""
        if asyncio.iscoroutinefunction(self.check_function):
            result = await self.check_function()
        else:
            result = self.check_function()
        
        if isinstance(result, dict):
            return result
        else:
            return {'message': str(result)}


class AdvancedHealthChecker:
    """Advanced health checker that manages multiple health checks."""
    
    def __init__(self, start_time: float | None = None):
        self.start_time = start_time or time.time()
        self.checkers: list[HealthChecker] = []
        self._last_report: HealthReport | None = None
        self._check_interval = 30.0  # Check every 30 seconds
        self._background_task: asyncio.Task | None = None
    
    def add_checker(self, checker: HealthChecker):
        """Add a health checker."""
        self.checkers.append(checker)
        _logger.info("health_checker_added", name=checker.name)
    
    def remove_checker(self, name: str):
        """Remove a health checker by name."""
        self.checkers = [c for c in self.checkers if c.name != name]
        _logger.info("health_checker_removed", name=name)
    
    async def check_health(self, include_details: bool = True) -> HealthReport:
        """Perform all health checks and return comprehensive report."""
        if not self.checkers:
            return HealthReport(
                status=HealthStatus.UNKNOWN,
                checks=[],
                uptime_seconds=time.time() - self.start_time,
                version="unknown",
                timestamp=time.time()
            )
        
        # Run all health checks concurrently
        tasks = [checker.check() for checker in self.checkers]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        checks = []
        overall_status = HealthStatus.HEALTHY
        dependencies = {}
        
        for result in check_results:
            if isinstance(result, Exception):
                # Health check itself failed
                check = HealthCheck(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(result)}",
                    duration_ms=0,
                    timestamp=time.time()
                )
                checks.append(check)
                overall_status = HealthStatus.UNHEALTHY
            else:
                checks.append(result)
                
                # Update overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                
                # Track dependencies
                if result.name in ['database', 'vector_store', 'grpc_service']:
                    dependencies[result.name] = result.status
        
        # Get version from settings
        try:
            from mindflow_backend.infra.config import get_settings
            version = getattr(get_settings(), 'app_version', 'unknown')
        except:
            version = 'unknown'
        
        report = HealthReport(
            status=overall_status,
            checks=checks,
            uptime_seconds=time.time() - self.start_time,
            version=version,
            timestamp=time.time(),
            dependencies=dependencies
        )
        
        self._last_report = report
        return report
    
    async def start_background_monitoring(self):
        """Start background health monitoring."""
        if self._background_task and not self._background_task.done():
            return
        
        self._background_task = asyncio.create_task(self._background_monitoring())
        _logger.info("health_monitoring_started")
    
    async def stop_background_monitoring(self):
        """Stop background health monitoring."""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
            _logger.info("health_monitoring_stopped")
    
    async def _background_monitoring(self):
        """Background task for continuous health monitoring."""
        while True:
            try:
                report = await self.check_health(include_details=False)
                
                # Log health status changes
                if self._last_report and self._last_report.status != report.status:
                    _logger.warning(
                        "health_status_changed",
                        from_status=self._last_report.status.value,
                        to_status=report.status.value,
                        uptime=report.uptime_seconds
                    )
                
                await asyncio.sleep(self._check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("health_monitoring_error", error=str(exc))
                await asyncio.sleep(self._check_interval)
    
    def get_last_report(self) -> HealthReport | None:
        """Get the last health report."""
        return self._last_report
    
    def setup_default_checkers(self, settings):
        """Setup default health checkers based on configuration."""
        # gRPC service checker
        grpc_checker = GrpcServiceHealthChecker(
            host=settings.grpc_host,
            port=settings.grpc_port,
            timeout_seconds=5.0
        )
        self.add_checker(grpc_checker)
        
        # Database checker
        if hasattr(settings, 'database') and hasattr(settings.database, 'url'):
            db_checker = DatabaseHealthChecker(
                database_url=settings.database.url,
                timeout_seconds=5.0
            )
            self.add_checker(db_checker)
        
        # Vector store checker
        if hasattr(settings, 'kuzudb_url'):
            vector_checker = VectorStoreHealthChecker(
                vector_db_url=settings.kuzudb_url,
                timeout_seconds=5.0
            )
            self.add_checker(vector_checker)
        
        # System checker
        system_checker = SystemHealthChecker(
            cpu_threshold=80.0,
            memory_threshold=80.0,
            timeout_seconds=5.0
        )
        self.add_checker(system_checker)
        
        _logger.info("default_health_checkers_setup", count=len(self.checkers))
