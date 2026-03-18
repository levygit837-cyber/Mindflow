"""API endpoint for planning metrics."""

from datetime import timedelta

from fastapi import APIRouter, Query

from mindflow_backend.orchestrator.planning.metrics import get_metrics_collector
from mindflow_backend.orchestrator.planning.cache import get_decision_cache

router = APIRouter(prefix="/planning/metrics", tags=["planning"])


@router.get("/summary")
async def get_metrics_summary(
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
):
    """Get summary of planning trigger metrics.
    
    Returns:
        - total_triggers: Number of times planning was triggered
        - total_decisions: Total number of trigger decisions
        - confirmation_rate: % of triggered plans that were confirmed
        - completion_rate: % of confirmed plans that were completed
        - avg_latency_ms: Average latency of trigger decisions
        - avg_confidence: Average confidence score
        - method_distribution: Count by method (llm/fallback/legacy)
    """
    collector = get_metrics_collector()
    time_window = timedelta(hours=hours)
    
    summary = await collector.get_metrics_summary(time_window)
    
    return {
        "time_window_hours": hours,
        **summary,
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    cache = get_decision_cache()
    
    return {
        "cache_size": cache.size(),
        "ttl_hours": cache._ttl.total_seconds() / 3600,
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear decision cache."""
    cache = get_decision_cache()
    cache.clear()
    
    return {"message": "Cache cleared successfully"}
