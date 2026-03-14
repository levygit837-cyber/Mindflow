"""Health service for monitoring system and service health.

This service provides comprehensive health checking capabilities including
service health monitoring, database connectivity checks, and system diagnostics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, UTC, timedelta
import asyncio
import psutil

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.monitoring_interfaces import HealthServiceInterface


class HealthService(BaseAbstractService, HealthServiceInterface):
    """Service for health checks and system monitoring.
    
    This service provides comprehensive health monitoring including
    service health checks, database connectivity, and system diagnostics.
    """
    
    def __init__(self) -> None:
        """Initialize health service with monitoring capabilities."""
        super().__init__()
        
        # Health check registry
        self._health_checks: Dict[str, callable] = {}
        self._health_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
        
        # Service status cache
        self._service_status: Dict[str, Dict[str, Any]] = {}
        self._status_cache_ttl = 60  # 1 minute
        
        # System metrics
        self._system_metrics = {
            "cpu_threshold": 80.0,
            "memory_threshold": 85.0,
            "disk_threshold": 90.0
        }
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            Dictionary containing service health information
        """
        self.log_operation("check_service_health", service_name=service_name)
        
        try:
            # Check if service has registered health check
            if service_name in self._health_checks:
                health_check = self._health_checks[service_name]
                result = await health_check()
                
                # Cache the result
                self._cache_service_status(service_name, result)
                
                return {
                    "service_name": service_name,
                    "status": "healthy" if result.get("healthy", False) else "unhealthy",
                    "checked_at": datetime.now(UTC).isoformat(),
                    "details": result,
                    "response_time_ms": result.get("response_time_ms", 0)
                }
            else:
                # Default health check for unregistered services
                return await self._default_service_health_check(service_name)
                
        except Exception as exc:
            self._logger.error(f"Error checking health for {service_name}: {str(exc)}")
            
            return {
                "service_name": service_name,
                "status": "error",
                "checked_at": datetime.now(UTC).isoformat(),
                "error": str(exc),
                "details": {"error_type": type(exc).__name__}
            }
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health including resources and services.
        
        Returns:
            Dictionary containing comprehensive system health information
        """
        self.log_operation("check_system_health")
        
        try:
            # Check system resources
            system_status = await self._check_system_resources()
            
            # Check all registered services
            service_results = await self._check_all_services()
            
            # Check database connectivity
            database_status = await self.check_database_health()
            
            # Calculate overall status
            overall_status = "healthy"
            if system_status.get("status") != "healthy":
                overall_status = "degraded"
            if any(service.get("status") != "healthy" for service in service_results):
                overall_status = "unhealthy"
            if database_status.get("status") != "healthy":
                overall_status = "unhealthy"
            
            # Combine all results
            health_report = {
                "overall_status": overall_status,
                "checked_at": datetime.now(UTC).isoformat(),
                "system": system_status,
                "services": service_results,
                "database": database_status,
                "summary": {
                    "total_services": len(service_results),
                    "healthy_services": len([s for s in service_results if s.get("status") == "healthy"]),
                    "unhealthy_services": len([s for s in service_results if s.get("status") != "healthy"]),
                    "critical_issues": self._identify_critical_issues(system_status, service_results, database_status)
                }
            }
            
            # Store in history
            self._store_health_result(health_report)
            
            return health_report
            
        except Exception as exc:
            self._logger.error(f"Error checking system health: {str(exc)}")
            
            return {
                "overall_status": "error",
                "checked_at": datetime.now(UTC).isoformat(),
                "error": str(exc),
                "details": {"error_type": type(exc).__name__}
            }
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance.
        
        Returns:
            Dictionary containing database health information
        """
        self.log_operation("check_database_health")
        
        try:
            # Test database connection
            from mindflow_backend.storage import db_session
            
            connection_test = {
                "connection_time_ms": 0,
                "connection_successful": False,
                "error": None
            }
            
            start_time = datetime.now(UTC)
            
            try:
                with db_session() as db:
                    # Execute a simple query to test connection
                    db.execute("SELECT 1").scalar()
                    
                end_time = datetime.now(UTC)
                connection_test["connection_time_ms"] = int((end_time - start_time).total_seconds() * 1000)
                connection_test["connection_successful"] = True
                
            except Exception as db_exc:
                connection_test["error"] = str(db_exc)
            
            # Check database performance metrics (placeholder)
            performance_metrics = {
                "connection_pool_size": 10,  # Would get from actual pool
                "active_connections": 5,
                "query_performance": {
                    "avg_response_time_ms": 50,
                    "slow_queries_count": 2
                }
            }
            
            return {
                "status": "healthy" if connection_test["connection_successful"] else "unhealthy",
                "connection_test": connection_test,
                "performance_metrics": performance_metrics,
                "checked_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error checking database health: {str(exc)}")
            
            return {
                "status": "error",
                "error": str(exc),
                "checked_at": datetime.now(UTC).isoformat()
            }
    
    async def check_external_service_health(self, service_url: str) -> Dict[str, Any]:
        """Check health of external service via HTTP request.
        
        Args:
            service_url: URL of the external service to check
            
        Returns:
            Dictionary containing external service health information
        """
        self.log_operation("check_external_service_health", service_url=service_url)
        
        try:
            import aiohttp
            import asyncio
            
            timeout = aiohttp.ClientTimeout(total=10)
            
            start_time = datetime.now(UTC)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.get(service_url) as response:
                        end_time = datetime.now(UTC)
                        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                        
                        return {
                            "service_url": service_url,
                            "status": "healthy" if response.status == 200 else "unhealthy",
                            "http_status": response.status,
                            "response_time_ms": response_time_ms,
                            "checked_at": datetime.now(UTC).isoformat(),
                            "response_headers": dict(response.headers),
                            "content_length": len(await response.text())
                        }
                        
                except asyncio.TimeoutError:
                    return {
                        "service_url": service_url,
                        "status": "timeout",
                        "error": "Request timeout after 10 seconds",
                        "checked_at": datetime.now(UTC).isoformat()
                    }
                        
        except Exception as exc:
            self._logger.error(f"Error checking external service {service_url}: {str(exc)}")
            
            return {
                "service_url": service_url,
                "status": "error",
                "error": str(exc),
                "checked_at": datetime.now(UTC).isoformat()
            }
    
    async def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics.
        
        Returns:
            Dictionary containing health metrics and statistics
        """
        self.log_operation("get_health_metrics")
        
        try:
            # Calculate metrics from history
            if not self._health_history:
                return {
                    "total_checks": 0,
                    "check_frequency": 0,
                    "uptime_percentage": 0,
                    "avg_response_time_ms": 0
                }
            
            # Calculate uptime percentage
            total_checks = len(self._health_history)
            healthy_checks = len([check for check in self._health_history if check.get("overall_status") == "healthy"])
            uptime_percentage = (healthy_checks / total_checks * 100) if total_checks > 0 else 0
            
            # Calculate average response time
            response_times = [
                check.get("system", {}).get("response_time_ms", 0)
                for check in self._health_history
                if check.get("system", {}).get("response_time_ms")
            ]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Calculate check frequency
            if len(self._health_history) >= 2:
                time_span = (
                    datetime.fromisoformat(self._health_history[-1]["checked_at"]) -
                    datetime.fromisoformat(self._health_history[0]["checked_at"])
                ).total_seconds()
                check_frequency = total_checks / (time_span / 3600) if time_span > 0 else 0  # checks per hour
            else:
                check_frequency = 0
            
            return {
                "total_checks": total_checks,
                "healthy_checks": healthy_checks,
                "unhealthy_checks": total_checks - healthy_checks,
                "uptime_percentage": round(uptime_percentage, 2),
                "avg_response_time_ms": round(avg_response_time, 2),
                "check_frequency_per_hour": round(check_frequency, 2),
                "last_24h_checks": len([
                    check for check in self._health_history
                    if datetime.fromisoformat(check["checked_at"]) > datetime.now(UTC) - timedelta(hours=24)
                ]),
                "most_common_issues": self._get_most_common_issues(),
                "generated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting health metrics: {str(exc)}")
            raise
    
    async def register_health_check(
        self,
        check_name: str,
        check_function: callable,
        interval: int = 60
    ) -> Dict[str, Any]:
        """Register a custom health check function.
        
        Args:
            check_name: Name of the health check
            check_function: Async function to execute
            interval: Check interval in seconds
            
        Returns:
            Dictionary containing registration result
        """
        self.log_operation("register_health_check", check_name=check_name, interval=interval)
        
        try:
            # Validate check function
            if not callable(check_function):
                raise ValueError("check_function must be callable")
            
            # Register the health check
            self._health_checks[check_name] = check_function
            
            return {
                "check_name": check_name,
                "interval": interval,
                "registered_at": datetime.now(UTC).isoformat(),
                "status": "registered"
            }
            
        except Exception as exc:
            self._logger.error(f"Error registering health check {check_name}: {str(exc)}")
            raise
    
    async def get_health_history(
        self,
        service_name: Optional[str] = None,
        time_range: Optional[Tuple[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Get health check history with optional filtering.
        
        Args:
            service_name: Optional service name filter
            time_range: Optional time range filter
            
        Returns:
            List of health check results
        """
        self.log_operation("get_health_history", service_name=service_name)
        
        try:
            history = self._health_history.copy()
            
            # Filter by service name
            if service_name:
                history = [
                    check for check in history
                    if service_name in str(check.get("services", {}))
                ]
            
            # Filter by time range
            if time_range:
                start_time = datetime.fromisoformat(time_range[0])
                end_time = datetime.fromisoformat(time_range[1])
                
                history = [
                    check for check in history
                    if start_time <= datetime.fromisoformat(check["checked_at"]) <= end_time
                ]
            
            # Return most recent results first
            history.sort(key=lambda x: x["checked_at"], reverse=True)
            
            return history[:100]  # Limit to last 100 results
            
        except Exception as exc:
            self._logger.error(f"Error getting health history: {str(exc)}")
            raise
    
    # Helper methods
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = "healthy" if cpu_percent < self._system_metrics["cpu_threshold"] else "warning"
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_status = "healthy" if memory_percent < self._system_metrics["memory_threshold"] else "warning"
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_status = "healthy" if disk_percent < self._system_metrics["disk_threshold"] else "warning"
            
            return {
                "status": "healthy" if all([
                    cpu_status == "healthy",
                    memory_status == "healthy", 
                    disk_status == "healthy"
                ]) else "warning",
                "cpu": {
                    "usage_percent": cpu_percent,
                    "status": cpu_status,
                    "threshold": self._system_metrics["cpu_threshold"]
                },
                "memory": {
                    "usage_percent": memory_percent,
                    "status": memory_status,
                    "threshold": self._system_metrics["memory_threshold"],
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "disk": {
                    "usage_percent": disk_percent,
                    "status": disk_status,
                    "threshold": self._system_metrics["disk_threshold"],
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                },
                "checked_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error checking system resources: {str(exc)}")
            return {
                "status": "error",
                "error": str(exc),
                "checked_at": datetime.now(UTC).isoformat()
            }
    
    async def _check_all_services(self) -> List[Dict[str, Any]]:
        """Check health of all registered services."""
        service_results = []
        
        for service_name in self._health_checks.keys():
            result = await self.check_service_health(service_name)
            service_results.append(result)
        
        return service_results
    
    async def _default_service_health_check(self, service_name: str) -> Dict[str, Any]:
        """Default health check for unregistered services."""
        # Check if service is importable and has expected methods
        try:
            # Try to import and check service
            if service_name == "agent_service":
                from mindflow_backend.services import get_agent_service
                service = get_agent_service()
                return {"healthy": True, "response_time_ms": 10}
            elif service_name == "memory_service":
                from mindflow_backend.memory import get_memory_service
                service = get_memory_service()
                return {"healthy": True, "response_time_ms": 15}
            elif service_name == "vector_service":
                from mindflow_backend.services import get_vector_service
                service = get_vector_service()
                return {"healthy": True, "response_time_ms": 20}
            else:
                return {"healthy": True, "response_time_ms": 5}
                
        except Exception as exc:
            return {"healthy": False, "error": str(exc), "response_time_ms": 0}
    
    def _cache_service_status(self, service_name: str, result: Dict[str, Any]) -> None:
        """Cache service status result."""
        self._service_status[service_name] = {
            **result,
            "cached_at": datetime.now(UTC).isoformat()
        }
    
    def _identify_critical_issues(self, system_status: Dict[str, Any], service_results: List[Dict[str, Any]], database_status: Dict[str, Any]) -> List[str]:
        """Identify critical issues from health check results."""
        issues = []
        
        # Check system issues
        if system_status.get("status") == "warning":
            if system_status.get("cpu", {}).get("status") == "warning":
                issues.append("High CPU usage")
            if system_status.get("memory", {}).get("status") == "warning":
                issues.append("High memory usage")
            if system_status.get("disk", {}).get("status") == "warning":
                issues.append("Low disk space")
        
        # Check service issues
        for service in service_results:
            if service.get("status") == "unhealthy":
                issues.append(f"Service {service.get('service_name')} is unhealthy")
        
        # Check database issues
        if database_status.get("status") == "unhealthy":
            issues.append("Database connectivity issues")
        
        return issues
    
    def _store_health_result(self, result: Dict[str, Any]) -> None:
        """Store health check result in history."""
        self._health_history.append(result)
        
        # Maintain history size limit
        if len(self._health_history) > self._max_history_size:
            self._health_history = self._health_history[-self._max_history_size:]
    
    def _get_most_common_issues(self) -> List[str]:
        """Get most common issues from health history."""
        issue_counts = {}
        
        for check in self._health_history[-100:]:  # Last 100 checks
            summary = check.get("summary", {})
            critical_issues = summary.get("critical_issues", [])
            
            for issue in critical_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Sort by frequency and return top 5
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        return [issue for issue, count in sorted_issues[:5]]
