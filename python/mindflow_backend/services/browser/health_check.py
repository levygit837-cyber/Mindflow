"""Health check service for LightPanda browser service.

Provides health check endpoints to monitor the status of the browser service,
Docker daemon connectivity, and active browser instances.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser import LightPandaDockerManager

_logger = get_logger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    checks: dict[str, Any]
    uptime_seconds: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "checks": self.checks,
            "uptime_seconds": self.uptime_seconds,
        }


class BrowserServiceHealthChecker:
    """Health checker for the LightPanda browser service.
    
    Provides health checks for:
    - Docker daemon connectivity
    - Active browser instances
    - Service uptime
    - Resource usage
    """
    
    def __init__(
        self,
        docker_manager: LightPandaDockerManager,
        service_name: str = "lightpanda-browser-service",
    ):
        """Initialize the health checker.
        
        Args:
            docker_manager: Docker manager instance
            service_name: Name of the service
        """
        self.docker_manager = docker_manager
        self.service_name = service_name
        self._start_time = time.time()
    
    async def check_health(self) -> HealthCheckResult:
        """Perform comprehensive health check.
        
        Returns:
            HealthCheckResult with detailed status
        """
        checks = {}
        overall_status = "healthy"
        
        # Check Docker daemon connectivity
        docker_check = await self._check_docker_connectivity()
        checks["docker_daemon"] = docker_check
        if docker_check["status"] != "healthy":
            overall_status = "degraded" if docker_check["status"] == "degraded" else "unhealthy"
        
        # Check active instances
        instances_check = await self._check_active_instances()
        checks["active_instances"] = instances_check
        if instances_check["status"] != "healthy":
            overall_status = "degraded"
        
        # Check service uptime
        uptime_check = self._check_uptime()
        checks["uptime"] = uptime_check
        
        # Check rate limiting
        rate_limit_check = self._check_rate_limit()
        checks["rate_limit"] = rate_limit_check
        
        return HealthCheckResult(
            service_name=self.service_name,
            status=overall_status,
            timestamp=datetime.utcnow(),
            checks=checks,
            uptime_seconds=time.time() - self._start_time,
        )
    
    async def _check_docker_connectivity(self) -> dict[str, Any]:
        """Check Docker daemon connectivity.
        
        Returns:
            Dictionary with connectivity status
        """
        try:
            client = await self.docker_manager._get_docker_client()
            if client is None:
                return {
                    "status": "unhealthy",
                    "message": "Docker client not available",
                    "connected": False,
                }
            
            # Try to ping Docker
            client.ping()
            
            return {
                "status": "healthy",
                "message": "Docker daemon connected",
                "connected": True,
            }
        except Exception as exc:
            _logger.error("docker_connectivity_check_failed", error=str(exc))
            return {
                "status": "unhealthy",
                "message": f"Docker daemon unreachable: {exc}",
                "connected": False,
            }
    
    async def _check_active_instances(self) -> dict[str, Any]:
        """Check active browser instances.
        
        Returns:
            Dictionary with instance status
        """
        try:
            active_instances = await self.docker_manager.list_active_instances()
            total_instances = len(self.docker_manager._instances)
            max_instances = self.docker_manager.max_instances
            
            # Calculate utilization
            utilization = (total_instances / max_instances) * 100 if max_instances > 0 else 0
            
            status = "healthy"
            message = f"{total_instances}/{max_instances} instances active"
            
            # Degraded if near max capacity
            if utilization >= 90:
                status = "degraded"
                message += " (near capacity)"
            # Unhealthy if at max capacity
            if total_instances >= max_instances:
                status = "degraded"
                message += " (at capacity)"
            
            return {
                "status": status,
                "message": message,
                "active_instances": len(active_instances),
                "total_instances": total_instances,
                "max_instances": max_instances,
                "utilization_percent": round(utilization, 2),
            }
        except Exception as exc:
            _logger.error("active_instances_check_failed", error=str(exc))
            return {
                "status": "unhealthy",
                "message": f"Failed to check instances: {exc}",
                "active_instances": 0,
                "total_instances": 0,
            }
    
    def _check_uptime(self) -> dict[str, Any]:
        """Check service uptime.
        
        Returns:
            Dictionary with uptime information
        """
        uptime = time.time() - self._start_time
        
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_uptime(uptime),
        }
    
    def _check_rate_limit(self) -> dict[str, Any]:
        """Check rate limiting status.
        
        Returns:
            Dictionary with rate limit information
        """
        now = time.time()
        recent_creations = len([
            ts for ts in self.docker_manager._creation_timestamps
            if now - ts < 60
        ])
        rate_limit = self.docker_manager.rate_limit_per_minute
        
        utilization = (recent_creations / rate_limit) * 100 if rate_limit > 0 else 0
        status = "healthy"
        
        if utilization >= 90:
            status = "degraded"
        
        return {
            "status": status,
            "recent_creations_last_minute": recent_creations,
            "rate_limit_per_minute": rate_limit,
            "utilization_percent": round(utilization, 2),
        }
    
    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format.
        
        Args:
            seconds: Uptime in seconds
            
        Returns:
            Formatted uptime string
        """
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        
        return " ".join(parts)
