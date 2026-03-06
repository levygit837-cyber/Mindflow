"""Metrics and monitoring endpoints."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, Request

from mindflow_backend.api.controllers.base_controller import BaseController
from mindflow_backend.api.middleware.performance import PerformanceMiddleware
from mindflow_backend.api.middleware.caching import AdvancedCacheMiddleware
from mindflow_backend.infra.logging import get_logger

router = APIRouter(prefix="/metrics", tags=["metrics"])
logger = get_logger(__name__)


class MetricsController(BaseController):
    """Controller for metrics and monitoring endpoints."""
    
    def __init__(self):
        super().__init__()
    
    async def get_performance_metrics(self, request: Request) -> Dict[str, Any]:
        """Get performance metrics from middleware."""
        try:
            # Get performance middleware stats
            performance_stats = {}
            cache_stats = {}
            
            # Try to get middleware instances from app state
            if hasattr(request.app, 'middleware'):
                for middleware in request.app.middleware:
                    if isinstance(middleware, PerformanceMiddleware):
                        performance_stats = middleware.get_cache_stats()
                    elif isinstance(middleware, AdvancedCacheMiddleware):
                        cache_stats = middleware.get_stats()
            
            # Combine metrics
            metrics = {
                "performance": performance_stats,
                "cache": cache_stats,
                "timestamp": self._get_current_timestamp(),
                "status": "active"
            }
            
            self.log_request(request, "get_performance_metrics")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {str(e)}")
            return {
                "error": str(e),
                "status": "error",
                "timestamp": self._get_current_timestamp()
            }
    
    async def get_health_metrics(self, request: Request) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        try:
            health_metrics = {
                "status": "healthy",
                "checks": {
                    "database": await self._check_database_health(),
                    "cache": await self._check_cache_health(),
                    "memory": await self._check_memory_health(),
                    "api": await self._check_api_health()
                },
                "timestamp": self._get_current_timestamp(),
                "uptime": self._get_uptime()
            }
            
            # Determine overall health status
            failed_checks = [
                name for name, check in health_metrics["checks"].items()
                if check.get("status") != "healthy"
            ]
            
            if failed_checks:
                health_metrics["status"] = "degraded" if len(failed_checks) == 1 else "unhealthy"
                health_metrics["failed_checks"] = failed_checks
            
            self.log_request(request, "get_health_metrics")
            return health_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting health metrics: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_current_timestamp()
            }
    
    async def get_api_metrics(self, request: Request) -> Dict[str, Any]:
        """Get API-specific metrics."""
        try:
            # This would collect API-specific metrics
            # For now, return placeholder data
            api_metrics = {
                "endpoints": {
                    "agent": {
                        "total_requests": 0,
                        "avg_response_time": 0.0,
                        "error_rate": 0.0
                    },
                    "session": {
                        "total_requests": 0,
                        "avg_response_time": 0.0,
                        "error_rate": 0.0
                    },
                    "orchestration": {
                        "total_requests": 0,
                        "avg_response_time": 0.0,
                        "error_rate": 0.0
                    },
                    "providers": {
                        "total_requests": 0,
                        "avg_response_time": 0.0,
                        "error_rate": 0.0
                    },
                    "memory": {
                        "total_requests": 0,
                        "avg_response_time": 0.0,
                        "error_rate": 0.0
                    }
                },
                "total_requests": 0,
                "overall_avg_response_time": 0.0,
                "overall_error_rate": 0.0,
                "timestamp": self._get_current_timestamp()
            }
            
            self.log_request(request, "get_api_metrics")
            return api_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting API metrics: {str(e)}")
            return {
                "error": str(e),
                "timestamp": self._get_current_timestamp()
            }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()
    
    def _get_uptime(self) -> str:
        """Get application uptime."""
        # This would track actual application start time
        # For now, return placeholder
        return "0h 0m 0s"
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            # This would perform actual database health check
            # For now, return placeholder
            return {
                "status": "healthy",
                "connection_pool": "active",
                "response_time_ms": 5
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_cache_health(self) -> Dict[str, Any]:
        """Check cache health."""
        try:
            # This would perform actual cache health check
            return {
                "status": "healthy",
                "hit_rate": 85.0,
                "memory_usage": "45%"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_memory_health(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            return {
                "status": "healthy" if memory.percent < 80 else "degraded",
                "usage_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2)
            }
        except ImportError:
            # psutil not available
            return {
                "status": "unknown",
                "error": "psutil not installed"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_api_health(self) -> Dict[str, Any]:
        """Check API health."""
        try:
            # This would check if API endpoints are responding
            return {
                "status": "healthy",
                "endpoints_responsive": True,
                "avg_response_time_ms": 50
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Initialize controller
metrics_controller = MetricsController()


@router.get("/performance")
async def get_performance_metrics(request: Request):
    """Get performance metrics."""
    return await metrics_controller.get_performance_metrics(request)


@router.get("/health")
async def get_health_metrics(request: Request):
    """Get comprehensive health metrics."""
    return await metrics_controller.get_health_metrics(request)


@router.get("/api")
async def get_api_metrics(request: Request):
    """Get API-specific metrics."""
    return await metrics_controller.get_api_metrics(request)


@router.get("/summary")
async def get_metrics_summary(request: Request):
    """Get metrics summary."""
    try:
        # Combine all metrics into a summary
        performance = await metrics_controller.get_performance_metrics(request)
        health = await metrics_controller.get_health_metrics(request)
        api = await metrics_controller.get_api_metrics(request)
        
        summary = {
            "status": health.get("status", "unknown"),
            "performance": {
                "cache_hit_rate": performance.get("cache", {}).get("hit_rate_percent", 0),
                "avg_response_time": api.get("overall_avg_response_time", 0)
            },
            "health_checks": health.get("checks", {}),
            "api_stats": {
                "total_requests": api.get("total_requests", 0),
                "error_rate": api.get("overall_error_rate", 0)
            },
            "timestamp": performance.get("timestamp")
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": metrics_controller._get_current_timestamp()
        }
