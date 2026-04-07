"""Resilience Dashboard API endpoints.

Provides REST API for monitoring circuit breakers, retry rates,
error distribution, and performance metrics.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

router = APIRouter(prefix="/resilience", tags=["resilience"])


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status response."""
    name: str
    state: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    failure_rate: float
    p95_latency: float
    p99_latency: float
    error_rate_window: float
    throughput: float
    error_distribution: dict[str, int]


class ResilienceOverview(BaseModel):
    """Resilience dashboard overview."""
    total_circuit_breakers: int
    open_circuit_breakers: int
    half_open_circuit_breakers: int
    closed_circuit_breakers: int
    circuit_breakers: list[CircuitBreakerStatus]
    retry_rate: float
    avg_p95_latency: float
    avg_p99_latency: float
    total_errors: int
    errors_by_category: dict[str, int]


class HealthStatus(BaseModel):
    """Health status response."""
    status: str
    circuit_breakers_healthy: bool
    retry_rate_acceptable: bool
    latency_acceptable: bool


# Storage for circuit breaker metrics (in production, use Redis/database)
_circuit_breaker_metrics: dict[str, dict[str, Any]] = {}


def register_circuit_breaker_metrics(
    name: str,
    metrics: dict[str, Any],
) -> None:
    """Register circuit breaker metrics for dashboard.

    Args:
        name: Circuit breaker name
        metrics: Metrics dictionary
    """
    _circuit_breaker_metrics[name] = metrics


@router.get("/dashboard/overview", response_model=ResilienceOverview)
async def get_resilience_overview() -> ResilienceOverview:
    """Get resilience dashboard overview.

    Returns:
        ResilienceOverview with all circuit breaker stats and aggregate metrics
    """
    try:
        circuit_breakers = []
        open_count = 0
        half_open_count = 0
        closed_count = 0
        total_p95 = 0.0
        total_p99 = 0.0
        total_errors = 0
        errors_by_category: dict[str, int] = {}

        for name, metrics in _circuit_breaker_metrics.items():
            state = metrics.get("state", "unknown")
            if state == "open":
                open_count += 1
            elif state == "half_open":
                half_open_count += 1
            else:
                closed_count += 1

            p95 = metrics.get("p95_latency", 0.0)
            p99 = metrics.get("p99_latency", 0.0)
            total_p95 += p95
            total_p99 += p99

            error_dist = metrics.get("error_distribution", {})
            for error_type, count in error_dist.items():
                total_errors += count
                errors_by_category[error_type] = (
                    errors_by_category.get(error_type, 0) + count
                )

            circuit_breakers.append(
                CircuitBreakerStatus(
                    name=name,
                    state=state,
                    total_calls=metrics.get("total_calls", 0),
                    successful_calls=metrics.get("successful_calls", 0),
                    failed_calls=metrics.get("failed_calls", 0),
                    success_rate=metrics.get("success_rate", 0.0),
                    failure_rate=metrics.get("failure_rate", 0.0),
                    p95_latency=p95,
                    p99_latency=p99,
                    error_rate_window=metrics.get("error_rate_window", 0.0),
                    throughput=metrics.get("throughput", 0.0),
                    error_distribution=error_dist,
                )
            )

        total_cb = len(_circuit_breaker_metrics)
        avg_p95 = total_p95 / max(total_cb, 1)
        avg_p99 = total_p99 / max(total_cb, 1)

        return ResilienceOverview(
            total_circuit_breakers=total_cb,
            open_circuit_breakers=open_count,
            half_open_circuit_breakers=half_open_count,
            closed_circuit_breakers=closed_count,
            circuit_breakers=circuit_breakers,
            retry_rate=0.0,  # TODO: Calculate from retry metrics
            avg_p95_latency=avg_p95,
            avg_p99_latency=avg_p99,
            total_errors=total_errors,
            errors_by_category=errors_by_category,
        )

    except Exception as e:
        _logger.error("resilience_dashboard_overview_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthStatus)
async def get_health_status() -> HealthStatus:
    """Get health status of resilience system.

    Returns:
        HealthStatus with overall health indicators
    """
    try:
        open_count = sum(
            1
            for m in _circuit_breaker_metrics.values()
            if m.get("state") == "open"
        )

        circuit_breakers_healthy = open_count == 0
        
        # Calculate retry rate across all circuit breakers
        total_retries = sum(m.get("retries", 0) for m in _circuit_breaker_metrics.values())
        total_calls = sum(m.get("total_calls", 1) for m in _circuit_breaker_metrics.values())
        retry_rate = (total_retries / max(total_calls, 1)) * 100
        retry_rate_acceptable = retry_rate < 5.0
        
        # Calculate P95 latency across all circuit breakers
        p95_latencies = [m.get("p95_latency", 0) for m in _circuit_breaker_metrics.values() if m.get("p95_latency", 0) > 0]
        avg_p95 = sum(p95_latencies) / max(len(p95_latencies), 1) if p95_latencies else 0
        latency_acceptable = avg_p95 < 200  # P95 < 200ms

        overall_healthy = (
            circuit_breakers_healthy
            and retry_rate_acceptable
            and latency_acceptable
        )

        return HealthStatus(
            status="healthy" if overall_healthy else "degraded",
            circuit_breakers_healthy=circuit_breakers_healthy,
            retry_rate_acceptable=retry_rate_acceptable,
            latency_acceptable=latency_acceptable,
        )

    except Exception as e:
        _logger.error("resilience_health_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breakers", response_model=list[CircuitBreakerStatus])
async def list_circuit_breakers() -> list[CircuitBreakerStatus]:
    """List all circuit breakers with their status.

    Returns:
        List of CircuitBreakerStatus
    """
    try:
        circuit_breakers = []
        for name, metrics in _circuit_breaker_metrics.items():
            circuit_breakers.append(
                CircuitBreakerStatus(
                    name=name,
                    state=metrics.get("state", "unknown"),
                    total_calls=metrics.get("total_calls", 0),
                    successful_calls=metrics.get("successful_calls", 0),
                    failed_calls=metrics.get("failed_calls", 0),
                    success_rate=metrics.get("success_rate", 0.0),
                    failure_rate=metrics.get("failure_rate", 0.0),
                    p95_latency=metrics.get("p95_latency", 0.0),
                    p99_latency=metrics.get("p99_latency", 0.0),
                    error_rate_window=metrics.get("error_rate_window", 0.0),
                    throughput=metrics.get("throughput", 0.0),
                    error_distribution=metrics.get("error_distribution", {}),
                )
            )
        return circuit_breakers

    except Exception as e:
        _logger.error("resilience_list_circuit_breakers_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breakers/{name}", response_model=CircuitBreakerStatus)
async def get_circuit_breaker(name: str) -> CircuitBreakerStatus:
    """Get specific circuit breaker status.

    Args:
        name: Circuit breaker name

    Returns:
        CircuitBreakerStatus for the specified circuit breaker
    """
    try:
        if name not in _circuit_breaker_metrics:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker '{name}' not found",
            )

        metrics = _circuit_breaker_metrics[name]
        return CircuitBreakerStatus(
            name=name,
            state=metrics.get("state", "unknown"),
            total_calls=metrics.get("total_calls", 0),
            successful_calls=metrics.get("successful_calls", 0),
            failed_calls=metrics.get("failed_calls", 0),
            success_rate=metrics.get("success_rate", 0.0),
            failure_rate=metrics.get("failure_rate", 0.0),
            p95_latency=metrics.get("p95_latency", 0.0),
            p99_latency=metrics.get("p99_latency", 0.0),
            error_rate_window=metrics.get("error_rate_window", 0.0),
            throughput=metrics.get("throughput", 0.0),
            error_distribution=metrics.get("error_distribution", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        _logger.error(
            "resilience_get_circuit_breaker_error",
            name=name,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str) -> dict[str, str]:
    """Reset a circuit breaker to closed state.

    Args:
        name: Circuit breaker name

    Returns:
        Success message
    """
    try:
        if name not in _circuit_breaker_metrics:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker '{name}' not found",
            )

        _circuit_breaker_metrics[name]["state"] = "closed"
        _circuit_breaker_metrics[name]["failed_calls"] = 0
        _circuit_breaker_metrics[name]["success_rate"] = 100.0
        _circuit_breaker_metrics[name]["failure_rate"] = 0.0

        _logger.info("circuit_breaker_reset", name=name)
        return {"message": f"Circuit breaker '{name}' reset to closed state"}

    except HTTPException:
        raise
    except Exception as e:
        _logger.error(
            "resilience_reset_circuit_breaker_error",
            name=name,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))