"""Resilience management API endpoints.

Provides REST API endpoints for managing gRPC resilience features
including circuit breakers, retry policies, bulkhead pattern, and fallback strategies.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.grpc.resilience.enhanced_circuit_breaker import AdaptiveThresholdType, EnhancedCircuitBreakerConfig
from mindflow_backend.grpc.resilience.advanced_retry import AdaptiveBackoffType, RetryConditionType, AdvancedRetryConfig
from mindflow_backend.grpc.resilience.bulkhead import BulkheadConfig
from mindflow_backend.grpc.resilience.fallback import FallbackConfig
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)
router = APIRouter(
    prefix="/resilience",
    tags=["resilience"],
    dependencies=protected_route_dependencies,
)


class CircuitBreakerConfigRequest(BaseModel):
    """Request model for circuit breaker configuration."""
    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: float = Field(default=60.0, ge=1.0)
    success_threshold: int = Field(default=3, ge=1)
    adaptive_threshold_type: AdaptiveThresholdType = AdaptiveThresholdType.PERCENTILE_BASED
    enable_dynamic_config: bool = True
    auto_tune_thresholds: bool = True


class RetryPolicyConfigRequest(BaseModel):
    """Request model for retry policy configuration."""
    max_attempts: int = Field(default=3, ge=1)
    base_delay: float = Field(default=0.1, ge=0.001)
    max_delay: float = Field(default=30.0, ge=0.001)
    adaptive_backoff_type: AdaptiveBackoffType = AdaptiveBackoffType.EXPONENTIAL_WITH_JITTER
    enable_adaptive_delay: bool = True
    retry_condition_type: RetryConditionType = RetryConditionType.ON_ERROR_TYPE
    enable_performance_retry: bool = True


class BulkheadConfigRequest(BaseModel):
    """Request model for bulkhead configuration."""
    max_concurrent: int = Field(default=100, ge=1)
    max_queue_size: int = Field(default=1000, ge=1)
    queue_timeout_seconds: float = Field(default=30.0, ge=0.001)
    execution_timeout_seconds: float = Field(default=60.0, ge=0.001)
    reject_when_full: bool = True


class FallbackConfigRequest(BaseModel):
    """Request model for fallback configuration."""
    enabled: bool = True
    fallback_timeout_seconds: float = Field(default=5.0, ge=0.001)
    max_fallback_attempts: int = Field(default=3, ge=1)
    enable_metrics: bool = True


@router.get("/status")
async def get_resilience_status() -> Dict[str, Any]:
    """Get current resilience configuration and metrics."""
    try:
        # Get global gRPC server instance
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server:
            raise HTTPException(status_code=404, detail="gRPC server not found")
        
        enhanced_status = server.get_enhanced_status()
        return enhanced_status.get("resilience", {})
        
    except Exception as e:
        _logger.error("get_resilience_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breaker/status")
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get circuit breaker status and metrics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.circuit_breaker:
            raise HTTPException(status_code=404, detail="Circuit breaker not available")
        
        return server.circuit_breaker.get_enhanced_metrics()
        
    except Exception as e:
        _logger.error("get_circuit_breaker_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breaker/config")
async def update_circuit_breaker_config(config: CircuitBreakerConfigRequest) -> Dict[str, Any]:
    """Update circuit breaker configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.circuit_breaker:
            raise HTTPException(status_code=404, detail="Circuit breaker not available")
        
        # Update circuit breaker configuration
        from mindflow_backend.grpc.resilience.enhanced_circuit_breaker import EnhancedCircuitBreakerConfig
        new_config = EnhancedCircuitBreakerConfig(
            failure_threshold=config.failure_threshold,
            recovery_timeout=config.recovery_timeout,
            success_threshold=config.success_threshold,
            adaptive_threshold_type=config.adaptive_threshold_type,
            enable_dynamic_config=config.enable_dynamic_config,
            auto_tune_thresholds=config.auto_tune_thresholds
        )
        
        server.circuit_breaker.update_config(new_config)
        
        _logger.info("circuit_breaker_config_updated", config=config.dict())
        
        return {"message": "Circuit breaker configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_circuit_breaker_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breaker/force-open")
async def force_open_circuit_breaker() -> Dict[str, Any]:
    """Force circuit breaker to open state (for testing)."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.circuit_breaker:
            raise HTTPException(status_code=404, detail="Circuit breaker not available")
        
        server.circuit_breaker._transition_to_open()
        
        _logger.info("circuit_breaker_forced_open")
        
        return {"message": "Circuit breaker forced to open state"}
        
    except Exception as e:
        _logger.error("force_open_circuit_breaker_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breaker/force-close")
async def force_close_circuit_breaker() -> Dict[str, Any]:
    """Force circuit breaker to closed state (for testing)."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.circuit_breaker:
            raise HTTPException(status_code=404, detail="Circuit breaker not available")
        
        server.circuit_breaker._transition_to_closed()
        
        _logger.info("circuit_breaker_forced_close")
        
        return {"message": "Circuit breaker forced to closed state"}
        
    except Exception as e:
        _logger.error("force_close_circuit_breaker_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retry-policy/status")
async def get_retry_policy_status() -> Dict[str, Any]:
    """Get retry policy status and metrics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.retry_policy:
            raise HTTPException(status_code=404, detail="Retry policy not available")
        
        return server.retry_policy.get_advanced_metrics()
        
    except Exception as e:
        _logger.error("get_retry_policy_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-policy/config")
async def update_retry_policy_config(config: RetryPolicyConfigRequest) -> Dict[str, Any]:
    """Update retry policy configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.retry_policy:
            raise HTTPException(status_code=404, detail="Retry policy not available")
        
        # Update retry policy configuration
        from mindflow_backend.grpc.resilience.advanced_retry import AdvancedRetryConfig
        new_config = AdvancedRetryConfig(
            max_attempts=config.max_attempts,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            adaptive_backoff_type=config.adaptive_backoff_type,
            enable_adaptive_delay=config.enable_adaptive_delay,
            retry_condition_type=config.retry_condition_type,
            enable_performance_retry=config.enable_performance_retry
        )
        
        server.retry_policy.update_config(new_config)
        
        _logger.info("retry_policy_config_updated", config=config.dict())
        
        return {"message": "Retry policy configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_retry_policy_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bulkhead/status")
async def get_bulkhead_status() -> Dict[str, Any]:
    """Get bulkhead status and metrics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.bulkhead:
            raise HTTPException(status_code=404, detail="Bulkhead not available")
        
        return {
            "status": server.bulkhead.get_status(),
            "metrics": server.bulkhead.get_metrics()
        }
        
    except Exception as e:
        _logger.error("get_bulkhead_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulkhead/config")
async def update_bulkhead_config(config: BulkheadConfigRequest) -> Dict[str, Any]:
    """Update bulkhead configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.bulkhead:
            raise HTTPException(status_code=404, detail="Bulkhead not available")
        
        # Update bulkhead configuration
        from mindflow_backend.grpc.resilience.bulkhead import BulkheadConfig
        new_config = BulkheadConfig(
            max_concurrent=config.max_concurrent,
            max_queue_size=config.max_queue_size,
            queue_timeout_seconds=config.queue_timeout_seconds,
            execution_timeout_seconds=config.execution_timeout_seconds,
            reject_when_full=config.reject_when_full,
            enable_metrics=True
        )
        
        server.bulkhead.update_config(new_config)
        
        _logger.info("bulkhead_config_updated", config=config.dict())
        
        return {"message": "Bulkhead configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_bulkhead_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fallback/status")
async def get_fallback_status() -> Dict[str, Any]:
    """Get fallback manager status and metrics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.fallback_manager:
            raise HTTPException(status_code=404, detail="Fallback manager not available")
        
        return server.fallback_manager.get_metrics()
        
    except Exception as e:
        _logger.error("get_fallback_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fallback/config")
async def update_fallback_config(config: FallbackConfigRequest) -> Dict[str, Any]:
    """Update fallback manager configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.fallback_manager:
            raise HTTPException(status_code=404, detail="Fallback manager not available")
        
        # Update fallback configuration
        from mindflow_backend.grpc.resilience.fallback import FallbackConfig
        new_config = FallbackConfig(
            enabled=config.enabled,
            fallback_timeout_seconds=config.fallback_timeout_seconds,
            max_fallback_attempts=config.max_fallback_attempts,
            enable_metrics=config.enable_metrics
        )
        
        server.fallback_manager.update_config(new_config)
        
        _logger.info("fallback_config_updated", config=config.dict())
        
        return {"message": "Fallback configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_fallback_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_resilience_metrics(
    start_time: Optional[float] = Query(None, description="Start timestamp"),
    end_time: Optional[float] = Query(None, description="End timestamp"),
    component: Optional[str] = Query(None, description="Component filter")
) -> Dict[str, Any]:
    """Get resilience metrics for analysis."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server:
            raise HTTPException(status_code=404, detail="gRPC server not found")
        
        metrics = {}
        
        # Collect metrics from all resilience components
        if server.circuit_breaker:
            metrics["circuit_breaker"] = server.circuit_breaker.get_enhanced_metrics()
        
        if server.retry_policy:
            metrics["retry_policy"] = server.retry_policy.get_advanced_metrics()
        
        if server.bulkhead:
            metrics["bulkhead"] = server.bulkhead.get_metrics()
        
        if server.fallback_manager:
            metrics["fallback_manager"] = server.fallback_manager.get_metrics()
        
        # Filter by component if specified
        if component:
            metrics = {k: v for k, v in metrics.items() if component.lower() in k.lower()}
        
        return metrics
        
    except Exception as e:
        _logger.error("get_resilience_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-metrics")
async def reset_resilience_metrics() -> Dict[str, Any]:
    """Reset all resilience metrics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server:
            raise HTTPException(status_code=404, detail="gRPC server not found")
        
        reset_components = []
        
        if server.circuit_breaker:
            server.circuit_breaker.reset_metrics()
            reset_components.append("circuit_breaker")
        
        if server.retry_policy:
            server.retry_policy.reset_metrics()
            reset_components.append("retry_policy")
        
        if server.fallback_manager:
            server.fallback_manager.reset_metrics()
            reset_components.append("fallback_manager")
        
        _logger.info("resilience_metrics_reset", components=reset_components)
        
        return {
            "message": "Resilience metrics reset successfully",
            "reset_components": reset_components
        }
        
    except Exception as e:
        _logger.error("reset_resilience_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check")
async def perform_resilience_health_check() -> Dict[str, Any]:
    """Perform comprehensive resilience health check."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server:
            raise HTTPException(status_code=404, detail="gRPC server not found")
        
        health_status = {
            "overall_health": "healthy",
            "components": {},
            "issues": []
        }
        
        # Check circuit breaker health
        if server.circuit_breaker:
            cb_metrics = server.circuit_breaker.get_enhanced_metrics()
            cb_health = "healthy"
            
            if cb_metrics["state"] == "open":
                cb_health = "degraded"
                health_status["issues"].append("Circuit breaker is open")
            elif cb_metrics["failure_rate"] > 50:
                cb_health = "warning"
                health_status["issues"].append("High failure rate detected")
            
            health_status["components"]["circuit_breaker"] = cb_health
        
        # Check retry policy health
        if server.retry_policy:
            retry_metrics = server.retry_policy.get_advanced_metrics()
            retry_health = "healthy"
            
            if retry_metrics["success_rate"] < 80:
                retry_health = "warning"
                health_status["issues"].append("Low retry success rate")
            
            health_status["components"]["retry_policy"] = retry_health
        
        # Check bulkhead health
        if server.bulkhead:
            bulkhead_status = server.bulkhead.get_status()
            bulkhead_health = "healthy"
            
            if bulkhead_status["utilization_percent"] > 90:
                bulkhead_health = "warning"
                health_status["issues"].append("High bulkhead utilization")
            
            health_status["components"]["bulkhead"] = bulkhead_health
        
        # Check fallback manager health
        if server.fallback_manager:
            fallback_metrics = server.fallback_manager.get_metrics()
            fallback_health = "healthy"
            
            if fallback_metrics["fallback_usage_rate"] > 50:
                fallback_health = "warning"
                health_status["issues"].append("High fallback usage rate")
            
            health_status["components"]["fallback_manager"] = fallback_health
        
        # Determine overall health
        if any(status == "degraded" for status in health_status["components"].values()):
            health_status["overall_health"] = "degraded"
        elif any(status == "warning" for status in health_status["components"].values()):
            health_status["overall_health"] = "warning"
        
        return health_status
        
    except Exception as e:
        _logger.error("resilience_health_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
