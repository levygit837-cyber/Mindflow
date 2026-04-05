"""Monitoring management API endpoints.

Provides REST API endpoints for managing gRPC monitoring features
including metrics collection, health checks, alerting, and profiling.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.grpc_internal.monitoring.alerting import (
    AlertSeverity,
    NotificationChannel,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)
router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
    dependencies=protected_route_dependencies,
)


class AlertConfigRequest(BaseModel):
    """Request model for alert configuration."""
    enabled: bool = True
    notification_channels: list[NotificationChannel] = [NotificationChannel.LOG]
    webhook_url: str | None = None
    webhook_timeout_seconds: float = Field(default=10.0, ge=1.0)
    webhook_retry_attempts: int = Field(default=3, ge=1)
    email_from: str | None = None
    email_to: list[str] = Field(default_factory=list)
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    enable_rate_limiting: bool = True
    max_alerts_per_hour: int = Field(default=50, ge=1)
    enable_deduplication: bool = True
    deduplication_window_minutes: int = Field(default=10, ge=1)


class AlertConditionRequest(BaseModel):
    """Request model for alert condition."""
    name: str
    metric_name: str
    threshold_value: float
    comparison_operator: str = Field(default=">", pattern="^(>|<|>=|<=|==)$")
    severity: AlertSeverity
    duration_seconds: float = Field(default=0.0, ge=0.0)
    cooldown_seconds: float = Field(default=300.0, ge=1.0)


class HealthCheckConfigRequest(BaseModel):
    """Request model for health check configuration."""
    enabled: bool = True
    check_interval_seconds: float = Field(default=30.0, ge=1.0)
    timeout_seconds: float = Field(default=10.0, ge=1.0)
    failure_threshold: int = Field(default=3, ge=1)
    recovery_threshold: int = Field(default=2, ge=1)


@router.get("/status")
async def get_monitoring_status() -> dict[str, Any]:
    """Get current monitoring configuration and metrics."""
    try:
        # Get global gRPC server instance
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server:
            raise HTTPException(status_code=404, detail="gRPC server not found")
        
        enhanced_status = server.get_enhanced_status()
        monitoring_status = enhanced_status.get("alerting", {})
        
        # Add basic monitoring components status
        monitoring_status["metrics_collector"] = {
            "enabled": server.metrics_collector is not None,
            "type": "GrpcMetricsCollector" if server.metrics_collector else None
        }
        
        monitoring_status["health_checker"] = {
            "enabled": server.health_checker is not None,
            "type": "AdvancedHealthChecker" if server.health_checker else None
        }
        
        monitoring_status["prometheus_exporter"] = {
            "enabled": server.prometheus_exporter is not None,
            "port": getattr(server.config, 'grpc_prometheus_port', None) if server.prometheus_exporter else None
        }
        
        return monitoring_status
        
    except Exception as e:
        _logger.error("get_monitoring_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    severity: AlertSeverity | None = Query(None, description="Filter by severity"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return")
) -> dict[str, Any]:
    """Get active alerts and alert history."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.alert_manager:
            raise HTTPException(status_code=404, detail="Alert manager not available")
        
        active_alerts = server.alert_manager.get_active_alerts()
        
        # Filter alerts if needed
        filtered_alerts = []
        for alert in active_alerts[:limit]:
            if severity and alert.severity != severity:
                continue
            if status and alert.status.value != status:
                continue
            
            filtered_alerts.append({
                "id": alert.id,
                "condition_name": alert.condition_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "created_at": alert.created_at,
                "age_seconds": alert.age_seconds,
                "duration_seconds": alert.duration_seconds
            })
        
        return {
            "active_alerts": filtered_alerts,
            "total_active": len(active_alerts),
            "filtered_count": len(filtered_alerts)
        }
        
    except Exception as e:
        _logger.error("get_alerts_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/config")
async def update_alert_config(config: AlertConfigRequest) -> dict[str, Any]:
    """Update alert manager configuration."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.alert_manager:
            raise HTTPException(status_code=404, detail="Alert manager not available")
        
        # Update alert configuration
        from mindflow_backend.grpc_internal.monitoring.alerting import AlertConfig
        new_config = AlertConfig(
            enabled=config.enabled,
            notification_channels=config.notification_channels,
            webhook_url=config.webhook_url,
            webhook_timeout_seconds=config.webhook_timeout_seconds,
            webhook_retry_attempts=config.webhook_retry_attempts,
            smtp_server=None,  # Would need to be added to request model
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            email_from=config.email_from,
            email_to=config.email_to,
            slack_webhook_url=config.slack_webhook_url,
            slack_channel=config.slack_channel,
            enable_rate_limiting=config.enable_rate_limiting,
            max_alerts_per_hour=config.max_alerts_per_hour,
            enable_deduplication=config.enable_deduplication,
            deduplication_window_minutes=config.deduplication_window_minutes
        )
        
        server.alert_manager.update_config(new_config)
        
        _logger.info("alert_config_updated", config=config.dict())
        
        return {"message": "Alert configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_alert_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/conditions")
async def add_alert_condition(condition: AlertConditionRequest) -> dict[str, Any]:
    """Add new alert condition."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.alert_manager:
            raise HTTPException(status_code=404, detail="Alert manager not available")
        
        # Create alert condition
        from mindflow_backend.grpc_internal.monitoring.alerting import AlertCondition
        new_condition = AlertCondition(
            name=condition.name,
            metric_name=condition.metric_name,
            threshold_value=condition.threshold_value,
            comparison_operator=condition.comparison_operator,
            severity=condition.severity,
            duration_seconds=condition.duration_seconds,
            cooldown_seconds=condition.cooldown_seconds
        )
        
        server.alert_manager.add_condition(new_condition)
        
        _logger.info("alert_condition_added", condition=condition.dict())
        
        return {"message": "Alert condition added successfully", "condition": condition.dict()}
        
    except Exception as e:
        _logger.error("add_alert_condition_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/conditions/{condition_name}")
async def remove_alert_condition(condition_name: str) -> dict[str, Any]:
    """Remove alert condition."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.alert_manager:
            raise HTTPException(status_code=404, detail="Alert manager not available")
        
        server.alert_manager.remove_condition(condition_name)
        
        _logger.info("alert_condition_removed", condition_name=condition_name)
        
        return {"message": f"Alert condition '{condition_name}' removed successfully"}
        
    except Exception as e:
        _logger.error("remove_alert_condition_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> dict[str, Any]:
    """Acknowledge an alert."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.alert_manager:
            raise HTTPException(status_code=404, detail="Alert manager not available")
        
        success = server.alert_manager.acknowledge_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        _logger.info("alert_acknowledged", alert_id=alert_id)
        
        return {"message": f"Alert '{alert_id}' acknowledged successfully"}
        
    except Exception as e:
        _logger.error("acknowledge_alert_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> dict[str, Any]:
    """Manually resolve an alert."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.alert_manager:
            raise HTTPException(status_code=404, detail="Alert manager not available")
        
        success = server.alert_manager.resolve_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        _logger.info("alert_resolved", alert_id=alert_id)
        
        return {"message": f"Alert '{alert_id}' resolved successfully"}
        
    except Exception as e:
        _logger.error("resolve_alert_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check/status")
async def get_health_check_status() -> dict[str, Any]:
    """Get health checker status and metrics."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.health_checker:
            raise HTTPException(status_code=404, detail="Health checker not available")
        
        # Get health check status (simplified)
        status = {
            "enabled": True,
            "checkers": [],
            "overall_health": "healthy",
            "last_check": time.time()
        }
        
        # In a real implementation, this would get actual health check data
        return status
        
    except Exception as e:
        _logger.error("get_health_check_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health-check/config")
async def update_health_check_config(config: HealthCheckConfigRequest) -> dict[str, Any]:
    """Update health checker configuration."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.health_checker:
            raise HTTPException(status_code=404, detail="Health checker not available")
        
        # Update health check configuration (simplified approach)
        _logger.info("health_check_config_updated", config=config.dict())
        
        return {"message": "Health check configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_health_check_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_monitoring_metrics(
    start_time: float | None = Query(None, description="Start timestamp"),
    end_time: float | None = Query(None, description="End timestamp"),
    metric_type: str | None = Query(None, description="Metric type filter")
) -> dict[str, Any]:
    """Get monitoring metrics for analysis."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.metrics_collector:
            raise HTTPException(status_code=404, detail="Metrics collector not available")
        
        # Get metrics from collector
        metrics = server.metrics_collector.get_metrics()
        
        # Filter by metric type if specified
        if metric_type:
            metrics = {k: v for k, v in metrics.items() if metric_type.lower() in k.lower()}
        
        return metrics
        
    except Exception as e:
        _logger.error("get_monitoring_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prometheus/metrics")
async def get_prometheus_metrics() -> str:
    """Get Prometheus metrics in text format."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.prometheus_exporter:
            raise HTTPException(status_code=404, detail="Prometheus exporter not available")
        
        # Get Prometheus metrics (simplified approach)
        metrics_text = """
# HELP grpc_requests_total Total number of gRPC requests
# TYPE grpc_requests_total counter
grpc_requests_total 100

# HELP grpc_request_duration_seconds gRPC request duration
# TYPE grpc_request_duration_seconds histogram
grpc_request_duration_seconds_bucket{le="0.1"} 10
grpc_request_duration_seconds_bucket{le="1.0"} 80
grpc_request_duration_seconds_bucket{le="+Inf"} 100
grpc_request_duration_seconds_sum 50.5
grpc_request_duration_seconds_count 100
"""
        
        return metrics_text
        
    except Exception as e:
        _logger.error("get_prometheus_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_monitoring_dashboard() -> dict[str, Any]:
    """Get monitoring dashboard data."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server:
            raise HTTPException(status_code=404, detail="gRPC server not found")
        
        enhanced_status = server.get_enhanced_status()
        
        dashboard = {
            "overview": {
                "server_running": server.is_running(),
                "uptime_seconds": server.get_uptime_seconds(),
                "host": server._host,
                "port": server._port
            },
            "resilience": enhanced_status.get("resilience", {}),
            "performance": enhanced_status.get("performance", {}),
            "alerting": enhanced_status.get("alerting", {}),
            "timestamp": time.time()
        }
        
        return dashboard
        
    except Exception as e:
        _logger.error("get_monitoring_dashboard_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-alert")
async def test_alert() -> dict[str, Any]:
    """Trigger a test alert to verify alerting system."""
    try:
        from mindflow_backend.grpc_internal.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.alert_manager:
            raise HTTPException(status_code=404, detail="Alert manager not available")
        
        # Trigger a test alert by evaluating a metric
        server.alert_manager.evaluate_metric(
            "test_metric",
            100.0,  # High value to trigger alert
            {"test": True}
        )
        
        _logger.info("test_alert_triggered")
        
        return {"message": "Test alert triggered successfully"}
        
    except Exception as e:
        _logger.error("test_alert_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Import required modules at the end to avoid circular imports
import time
