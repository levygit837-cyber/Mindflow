"""Health check utilities for MindFlow backend.

Generic health check functionality that can be used across the system.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import psutil

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HealthStatus:
    """Health status of a component or service."""
    
    def __init__(
        self,
        name: str,
        status: str = "unknown",
        message: str = "",
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ):
        self.name = name
        self.status = status  # "healthy", "unhealthy", "degraded", "unknown"
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now(UTC)
        self.response_time_ms = 0.0
        self.error_count = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "error_count": self.error_count,
        }
    
    @classmethod
    def healthy(cls, name: str, message: str = "OK", **details: Any) -> "HealthStatus":
        """Create healthy status."""
        return cls(name, "healthy", message, details)
    
    @classmethod
    def unhealthy(cls, name: str, message: str, **details: Any) -> "HealthStatus":
        """Create unhealthy status."""
        return cls(name, "unhealthy", message, details)
    
    @classmethod
    def degraded(cls, name: str, message: str, **details: Any) -> "HealthStatus":
        """Create degraded status."""
        return cls(name, "degraded", message, details)


class HealthChecker(ABC):
    """Abstract base class for health checkers."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def check(self) -> HealthStatus:
        """Perform health check."""
        pass
    
    async def check_with_timeout(self, timeout: float = 5.0) -> HealthStatus:
        """Perform health check with timeout."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(self.check(), timeout=timeout)
            result.response_time_ms = (time.time() - start_time) * 1000
            return result
        except TimeoutError:
            return HealthStatus.unhealthy(
                self.name,
                f"Health check timed out after {timeout}s",
                timeout=timeout,
            )
        except Exception as exc:
            return HealthStatus.unhealthy(
                self.name,
                f"Health check failed: {str(exc)}",
                error=str(exc),
            )


class DatabaseHealthChecker(HealthChecker):
    """Health checker for database connections."""
    
    def __init__(self, name: str, connection_func: callable):
        super().__init__(name)
        self.connection_func = connection_func
    
    async def check(self) -> HealthStatus:
        """Check database health."""
        try:
            start_time = time.time()
            
            # Try to execute a simple query
            async with self.connection_func() as conn:
                await conn.execute("SELECT 1")
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthStatus.healthy(
                self.name,
                "Database connection successful",
                response_time_ms=response_time,
            )
            
        except Exception as exc:
            return HealthStatus.unhealthy(
                self.name,
                f"Database connection failed: {str(exc)}",
                error=str(exc),
            )


class HTTPHealthChecker(HealthChecker):
    """Health checker for HTTP endpoints."""
    
    def __init__(self, name: str, url: str, expected_status: int = 200):
        super().__init__(name)
        self.url = url
        self.expected_status = expected_status
    
    async def check(self) -> HealthStatus:
        """Check HTTP endpoint health."""
        try:
            import aiohttp
            
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    response_time = (time.time() - start_time) * 1000
                    content = await response.text()
                    
                    if response.status == self.expected_status:
                        return HealthStatus.healthy(
                            self.name,
                            f"HTTP endpoint healthy (status {response.status})",
                            url=self.url,
                            status_code=response.status,
                            response_time_ms=response_time,
                            content_length=len(content),
                        )
                    else:
                        return HealthStatus.unhealthy(
                            self.name,
                            f"HTTP endpoint returned status {response.status}, expected {self.expected_status}",
                            url=self.url,
                            status_code=response.status,
                            response_time_ms=response_time,
                        )
        
        except Exception as exc:
            return HealthStatus.unhealthy(
                self.name,
                f"HTTP health check failed: {str(exc)}",
                url=self.url,
                error=str(exc),
            )


class RedisHealthChecker(HealthChecker):
    """Health checker for Redis connections."""
    
    def __init__(self, name: str, redis_client: callable):
        super().__init__(name)
        self.redis_client = redis_client
    
    async def check(self) -> HealthStatus:
        """Check Redis health."""
        try:
            start_time = time.time()
            
            redis = await self.redis_client()
            await redis.ping()
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthStatus.healthy(
                self.name,
                "Redis connection successful",
                response_time_ms=response_time,
            )
            
        except Exception as exc:
            return HealthStatus.unhealthy(
                self.name,
                f"Redis connection failed: {str(exc)}",
                error=str(exc),
            )


class SystemHealthChecker(HealthChecker):
    """Health checker for system resources."""
    
    def __init__(self, name: str = "system"):
        super().__init__(name)
    
    async def check(self) -> HealthStatus:
        """Check system health."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Load average (Unix systems)
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                load_avg = (0, 0, 0)  # Not available on Windows
            
            # Determine overall health
            issues = []
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            if memory_percent > 90:
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            if disk_percent > 90:
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            if issues:
                return HealthStatus.degraded(
                    self.name,
                    f"System resources degraded: {'; '.join(issues)}",
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    disk_percent=disk_percent,
                    load_average=load_avg,
                    issues=issues,
                )
            else:
                return HealthStatus.healthy(
                    self.name,
                    "System resources healthy",
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    disk_percent=disk_percent,
                    load_average=load_avg,
                )
        
        except Exception as exc:
            return HealthStatus.unhealthy(
                self.name,
                f"System health check failed: {str(exc)}",
                error=str(exc),
            )


class ProcessHealthChecker(HealthChecker):
    """Health checker for process monitoring."""
    
    def __init__(self, name: str, process_id: str, port: int, pid: int | None = None):
        super().__init__(name)
        self.process_id = process_id
        self.port = port
        self.pid = pid
    
    async def check(self) -> HealthStatus:
        """Check process health."""
        try:
            details = {
                "process_id": self.process_id,
                "port": self.port,
                "pid": self.pid,
            }
            
            # Check if process is running (if PID is available)
            if self.pid:
                try:
                    process = psutil.Process(self.pid)
                    details.update({
                        "cpu_percent": process.cpu_percent(),
                        "memory_mb": process.memory_info().rss / 1024 / 1024,
                        "status": process.status(),
                        "create_time": datetime.fromtimestamp(process.create_time(), UTC).isoformat(),
                    })
                except psutil.NoSuchProcess:
                    return HealthStatus.unhealthy(
                        self.name,
                        f"Process {self.pid} not found",
                        **details
                    )
            
            # Check if port is available
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', self.port))
            sock.close()
            
            if result == 0:
                details["port_status"] = "open"
                return HealthStatus.healthy(
                    self.name,
                    "Process is healthy and port is accessible",
                    **details
                )
            else:
                details["port_status"] = "closed"
                return HealthStatus.unhealthy(
                    self.name,
                    f"Port {self.port} is not accessible",
                    **details
                )
        
        except Exception as exc:
            return HealthStatus.unhealthy(
                self.name,
                f"Process health check failed: {str(exc)}",
                error=str(exc),
            )


class HealthCheckManager:
    """Manager for multiple health checkers."""
    
    def __init__(self):
        self.checkers: list[HealthChecker] = []
        self.last_check: datetime | None = None
        self.last_results: list[HealthStatus] = []
    
    def add_checker(self, checker: HealthChecker) -> None:
        """Add a health checker."""
        self.checkers.append(checker)
    
    def remove_checker(self, name: str) -> bool:
        """Remove a health checker by name."""
        for i, checker in enumerate(self.checkers):
            if checker.name == name:
                del self.checkers[i]
                return True
        return False
    
    async def check_all(self, timeout: float = 5.0) -> list[HealthStatus]:
        """Run all health checks."""
        if not self.checkers:
            return []
        
        tasks = [
            checker.check_with_timeout(timeout) 
            for checker in self.checkers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to unhealthy status
        health_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                health_results.append(HealthStatus.unhealthy(
                    self.checkers[i].name,
                    f"Health check error: {str(result)}",
                    error=str(result),
                ))
            else:
                health_results.append(result)
        
        self.last_check = datetime.now(UTC)
        self.last_results = health_results
        
        return health_results
    
    async def check_single(self, name: str, timeout: float = 5.0) -> HealthStatus | None:
        """Run a single health check."""
        for checker in self.checkers:
            if checker.name == name:
                return await checker.check_with_timeout(timeout)
        return None
    
    def get_overall_status(self) -> str:
        """Get overall health status."""
        if not self.last_results:
            return "unknown"
        
        statuses = [result.status for result in self.last_results]
        
        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        elif any(status == "degraded" for status in statuses):
            return "degraded"
        else:
            return "unknown"
    
    def get_summary(self) -> dict[str, Any]:
        """Get health check summary."""
        if not self.last_results:
            return {
                "overall_status": "unknown",
                "last_check": None,
                "checks": [],
                "healthy_count": 0,
                "unhealthy_count": 0,
                "degraded_count": 0,
                "unknown_count": 0,
            }
        
        status_counts = {
            "healthy": 0,
            "unhealthy": 0,
            "degraded": 0,
            "unknown": 0,
        }
        
        for result in self.last_results:
            status_counts[result.status] += 1
        
        return {
            "overall_status": self.get_overall_status(),
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "checks": [result.to_dict() for result in self.last_results],
            **status_counts,
        }


# Global health check manager instance
_health_manager: HealthCheckManager | None = None


def get_health_manager() -> HealthCheckManager:
    """Get or create global health manager instance."""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    return _health_manager
