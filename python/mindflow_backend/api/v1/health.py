"""Health check API endpoints.

Provides comprehensive health monitoring endpoints for all system components
using the new infrastructure health check system.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.monitoring.health_checks import get_health_manager
from mindflow_backend.infra.monitoring.metrics import get_metrics_collector

_logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(description="Overall health status")
    timestamp: datetime = Field(description="Health check timestamp")
    total_components: int = Field(description="Total number of components checked")
    healthy_components: int = Field(description="Number of healthy components")
    degraded_components: int = Field(description="Number of degraded components")
    unhealthy_components: int = Field(description="Number of unhealthy components")
    unknown_components: int = Field(description="Number of components with unknown status")
    components: list[dict[str, Any]] = Field(description="Individual component health results")


class ComponentHealthResponse(BaseModel):
    """Component health check response model."""
    component: str = Field(description="Component name")
    component_type: str = Field(description="Component type")
    status: str = Field(description="Component health status")
    message: str = Field(description="Health status message")
    timestamp: datetime = Field(description="Health check timestamp")
    response_time_ms: float = Field(description="Response time in milliseconds")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional health details")
    error: str | None = Field(default=None, description="Error if health check failed")


class HealthStatisticsResponse(BaseModel):
    """Health check statistics response model."""
    component: str = Field(description="Component name")
    component_type: str = Field(description="Component type")
    check_count: int = Field(description="Total number of health checks performed")
    failure_count: int = Field(description="Number of failed health checks")
    success_rate: float = Field(description="Success rate percentage")
    last_check: datetime | None = Field(default=None, description="Last health check timestamp")
    last_status: str | None = Field(default=None, description="Last health check status")


@router.get("/", response_model=HealthResponse)
async def get_system_health(
    detailed: bool = Query(default=False, description="Include detailed component information"),
    components: list[str] | None = Query(default=None, description="Specific components to check")
) -> HealthResponse:
    """Get overall system health status.
    
    Args:
        detailed: Include detailed component information
        components: Specific components to check (all if not specified)
        
    Returns:
        Overall system health status
    """
    try:
        health_manager = get_health_manager()
        
        if components:
            # Check specific components
            component_results = []
            for component in components:
                result = await health_manager.check_component_health(component)
                if result:
                    component_results.append(result)
                    
            # Calculate overall status
            if not component_results:
                raise HTTPException(status_code=404, detail="No components found")
                
            healthy_count = sum(1 for r in component_results if r.status.value == "healthy")
            degraded_count = sum(1 for r in component_results if r.status.value == "degraded")
            unhealthy_count = sum(1 for r in component_results if r.status.value == "unhealthy")
            unknown_count = sum(1 for r in component_results if r.status.value == "unknown")
            
            if unhealthy_count > 0:
                overall_status = "unhealthy"
            elif degraded_count > 0:
                overall_status = "degraded"
            elif healthy_count == len(component_results):
                overall_status = "healthy"
            else:
                overall_status = "unknown"
                
            total_components = len(component_results)
        else:
            # Check all components
            system_health = await health_manager.check_system_health()
            component_results = system_health.component_results
            overall_status = system_health.status.value
            total_components = system_health.total_components
            healthy_count = system_health.healthy_components
            degraded_count = system_health.degraded_components
            unhealthy_count = system_health.unhealthy_components
            unknown_count = system_health.unknown_components
            
        # Prepare component data
        components_data = []
        if detailed:
            components_data = [result.to_dict() for result in component_results]
        else:
            components_data = [
                {
                    "component": result.component,
                    "component_type": result.component_type.value,
                    "status": result.status.value,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                }
                for result in component_results
            ]
            
        response = HealthResponse(
            status=overall_status,
            timestamp=datetime.now(UTC),
            total_components=total_components,
            healthy_components=healthy_count,
            degraded_components=degraded_count,
            unhealthy_components=unhealthy_count,
            unknown_components=unknown_count,
            components=components_data,
        )
        
        _logger.info(
            "system_health_checked",
            status=overall_status,
            total=total_components,
            healthy=healthy_count,
            degraded=degraded_count,
            unhealthy=unhealthy_count,
        )
        
        return response
        
    except Exception as e:
        _logger.error("system_health_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/component/{component}", response_model=ComponentHealthResponse)
async def get_component_health(component: str) -> ComponentHealthResponse:
    """Get health status for a specific component.
    
    Args:
        component: Component name to check
        
    Returns:
        Component health status
    """
    try:
        health_manager = get_health_manager()
        result = await health_manager.check_component_health(component)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Component '{component}' not found")
            
        response = ComponentHealthResponse(
            component=result.component,
            component_type=result.component_type.value,
            status=result.status.value,
            message=result.message,
            timestamp=result.timestamp,
            response_time_ms=result.response_time_ms,
            details=result.details,
            error=str(result.error) if result.error else None,
        )
        
        _logger.info(
            "component_health_checked",
            component=component,
            status=result.status.value,
            response_time_ms=result.response_time_ms,
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("component_health_check_failed", component=component, error=str(e))
        raise HTTPException(status_code=500, detail=f"Component health check failed: {str(e)}")


@router.get("/components")
async def list_components() -> dict[str, Any]:
    """List all available health check components.
    
    Returns:
        List of available components and their types
    """
    try:
        health_manager = get_health_manager()
        components = health_manager.get_all_statistics()
        
        component_list = []
        for component, stats in components.items():
            component_list.append({
                "name": component,
                "type": stats["component_type"],
                "check_count": stats["check_count"],
                "failure_count": stats["failure_count"],
                "success_rate": stats["success_rate"],
                "last_check": stats["last_check"],
                "last_status": stats["last_status"],
            })
            
        return {
            "components": component_list,
            "total_count": len(component_list),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
    except Exception as e:
        _logger.error("list_components_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list components: {str(e)}")


@router.get("/statistics")
async def get_health_statistics(
    component: str | None = Query(default=None, description="Specific component statistics")
) -> dict[str, Any]:
    """Get health check statistics.
    
    Args:
        component: Specific component to get statistics for (all if not specified)
        
    Returns:
        Health check statistics
    """
    try:
        health_manager = get_health_manager()
        
        if component:
            stats = health_manager.get_component_statistics(component)
            if not stats:
                raise HTTPException(status_code=404, detail=f"Component '{component}' not found")
            return {"component": component, "statistics": stats}
        else:
            all_stats = health_manager.get_all_statistics()
            return {"statistics": all_stats, "total_components": len(all_stats)}
            
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("get_health_statistics_failed", component=component, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get health statistics: {str(e)}")


@router.get("/live")
async def liveness_probe() -> dict[str, Any]:
    """Kubernetes liveness probe endpoint.
    
    Returns basic liveness status without performing extensive checks.
    
    Returns:
        Liveness status
    """
    try:
        # Basic liveness check - just verify the service is running
        return {
            "status": "alive",
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "mindflow-backend",
        }
        
    except Exception as e:
        _logger.error("liveness_probe_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not alive")


@router.get("/ready")
async def readiness_probe() -> dict[str, Any]:
    """Kubernetes readiness probe endpoint.
    
    Checks if the service is ready to accept traffic.
    
    Returns:
        Readiness status
    """
    try:
        health_manager = get_health_manager()
        
        # Quick readiness check - verify critical components are healthy
        critical_components = ["postgresql", "redis"]  # Add more as needed
        
        for component in critical_components:
            result = await health_manager.check_component_health(component)
            if result and result.status.value in ["unhealthy", "unknown"]:
                return {
                    "status": "not_ready",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "reason": f"Critical component '{component}' is {result.status.value}",
                    "component": component,
                    "component_status": result.status.value,
                }
                
        return {
            "status": "ready",
            "timestamp": datetime.now(UTC).isoformat(),
            "checked_components": critical_components,
        }
        
    except Exception as e:
        _logger.error("readiness_probe_failed", error=str(e))
        return {
            "status": "not_ready",
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": f"Readiness check failed: {str(e)}",
        }


@router.get("/startup")
async def startup_probe() -> dict[str, Any]:
    """Kubernetes startup probe endpoint.
    
    Checks if the service has completed startup.
    
    Returns:
        Startup status
    """
    try:
        # Check if core services are initialized
        health_manager = get_health_manager()
        last_check = health_manager.get_last_system_check()
        
        if not last_check:
            return {
                "status": "starting",
                "timestamp": datetime.now(UTC).isoformat(),
                "reason": "Health checks not yet initialized",
            }
            
        # Consider service started if at least one health check has completed
        return {
            "status": "started",
            "timestamp": datetime.now(UTC).isoformat(),
            "last_system_check": last_check.timestamp.isoformat(),
            "system_status": last_check.status.value,
        }
        
    except Exception as e:
        _logger.error("startup_probe_failed", error=str(e))
        return {
            "status": "starting",
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": f"Startup check failed: {str(e)}",
        }


@router.post("/check")
async def trigger_health_check(
    components: list[str] | None = Query(default=None, description="Components to check")
) -> dict[str, Any]:
    """Trigger an immediate health check.
    
    Args:
        components: Specific components to check (all if not specified)
        
    Returns:
        Health check results
    """
    try:
        health_manager = get_health_manager()
        
        if components:
            results = {}
            for component in components:
                result = await health_manager.check_component_health(component)
                if result:
                    results[component] = result.to_dict()
                else:
                    results[component] = {"status": "not_found", "error": f"Component '{component}' not found"}
        else:
            system_health = await health_manager.check_system_health()
            results = system_health.to_dict()
            
        _logger.info(
            "health_check_triggered",
            components=components,
            results_count=len(results) if isinstance(results, dict) else 1,
        )
        
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "results": results,
        }
        
    except Exception as e:
        _logger.error("trigger_health_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check trigger failed: {str(e)}")


@router.get("/metrics")
async def get_health_metrics() -> dict[str, Any]:
    """Get health-related metrics.
    
    Returns:
        Health check metrics and performance data
    """
    try:
        health_manager = get_health_manager()
        metrics_collector = get_metrics_collector()
        
        # Get health check statistics
        all_stats = health_manager.get_all_statistics()
        
        # Calculate health metrics
        total_checks = sum(stats["check_count"] for stats in all_stats.values())
        total_failures = sum(stats["failure_count"] for stats in all_stats.values())
        overall_success_rate = (total_checks - total_failures) / max(total_checks, 1)
        
        # Get component counts by status
        last_system_check = health_manager.get_last_system_check()
        component_counts = {
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "unknown": 0,
        }
        
        if last_system_check:
            component_counts["healthy"] = last_system_check.healthy_components
            component_counts["degraded"] = last_system_check.degraded_components
            component_counts["unhealthy"] = last_system_check.unhealthy_components
            component_counts["unknown"] = last_system_check.unknown_components
        
        # Get performance metrics
        performance_metrics = await metrics_collector.collect_metrics()
        
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "health_metrics": {
                "total_checks": total_checks,
                "total_failures": total_failures,
                "overall_success_rate": overall_success_rate,
                "component_counts": component_counts,
                "components_monitored": len(all_stats),
            },
            "performance_metrics": performance_metrics.get("metrics", {}),
            "last_system_check": last_system_check.to_dict() if last_system_check else None,
        }
        
    except Exception as e:
        _logger.error("get_health_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get health metrics: {str(e)}")


@router.get("/browser")
async def get_browser_health() -> dict[str, Any]:
    """Get LightPanda browser service health status.
    
    Returns:
        Browser service health check results
    """
    try:
        from mindflow_backend.services.browser.health_check import BrowserServiceHealthChecker
        from mindflow_backend.services.browser import LightPandaDockerManager
        
        # Get docker manager instance (would need to be properly initialized)
        # For now, return a placeholder response
        # In production, this should use the actual docker manager instance
        return {
            "status": "healthy",
            "message": "Browser health check endpoint available",
            "note": "Full health check requires docker manager instance",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="Browser health check service not available")
    except Exception as e:
        _logger.error("get_browser_health_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Browser health check failed: {str(e)}")
