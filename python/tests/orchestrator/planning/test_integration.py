"""Integration tests for planning trigger system."""

from datetime import timedelta

import pytest

from mindflow_backend.orchestrator.planning.analyzer import get_planning_analyzer
from mindflow_backend.orchestrator.planning.cache import get_decision_cache
from mindflow_backend.orchestrator.planning.metrics import get_metrics_collector
from mindflow_backend.schemas.orchestration.planning import PlanningAnalysisRequest


@pytest.mark.asyncio
async def test_end_to_end_trigger_flow():
    """Test complete flow: analyze → cache → metrics."""
    analyzer = get_planning_analyzer()
    cache = get_decision_cache()
    metrics = get_metrics_collector()
    
    # Clear cache
    cache.clear()
    
    # First request (LLM)
    request = PlanningAnalysisRequest(
        message="Implementar sistema completo de autenticação JWT"
    )
    
    decision1 = await analyzer.should_trigger_planning(request)
    
    assert decision1.requires_planning is True
    assert decision1.confidence > 0.0
    assert len(decision1.reasoning) > 0
    
    # Second request (cache hit)
    decision2 = await analyzer.should_trigger_planning(request)
    
    assert decision2.requires_planning == decision1.requires_planning
    assert decision2.confidence == decision1.confidence
    
    # Verify cache
    assert cache.size() > 0


@pytest.mark.asyncio
async def test_cache_expiration():
    """Test cache TTL expiration."""
    from datetime import timedelta

    from mindflow_backend.orchestrator.planning.cache import PlanningDecisionCache
    
    # Create cache with 1 second TTL
    cache = PlanningDecisionCache(ttl=timedelta(seconds=1))
    analyzer = get_planning_analyzer()
    
    request = PlanningAnalysisRequest(message="Test message")
    
    # First call
    decision1 = await analyzer.should_trigger_planning(request)
    cache.set(request.message, decision1)
    
    # Immediate second call (cache hit)
    cached = cache.get(request.message)
    assert cached is not None
    
    # Wait for expiration
    import asyncio
    await asyncio.sleep(1.1)
    
    # Third call (cache miss)
    cached = cache.get(request.message)
    assert cached is None


@pytest.mark.asyncio
async def test_metrics_tracking():
    """Test metrics are tracked correctly."""
    metrics = get_metrics_collector()
    
    # Track a decision
    await metrics.track_trigger_decision(
        session_id="test-session",
        trigger_decision=True,
        confidence=0.85,
        latency_ms=850.0,
        method_used="llm",
    )
    
    # Get summary
    summary = await metrics.get_metrics_summary(timedelta(hours=1))
    
    assert summary["total_triggers"] >= 1
    assert summary["total_decisions"] >= 1
    assert "llm" in summary["method_distribution"]


@pytest.mark.asyncio
async def test_fallback_on_error():
    """Test fallback when LLM fails."""
    analyzer = get_planning_analyzer()
    
    # Mock LLM to fail
    async def mock_call_llm(*args, **kwargs):
        raise Exception("LLM unavailable")
    
    original_call = analyzer._call_llm
    analyzer._call_llm = mock_call_llm
    
    try:
        request = PlanningAnalysisRequest(
            message="Implementar feature X com múltiplos arquivos"
        )
        
        decision = await analyzer.should_trigger_planning(request)
        
        # Should use fallback
        assert "fallback" in decision.reasoning.lower()
        assert decision.confidence <= 0.6
        
    finally:
        analyzer._call_llm = original_call


@pytest.mark.asyncio
async def test_cache_normalization():
    """Test cache normalizes messages correctly."""
    cache = get_decision_cache()
    cache.clear()
    
    from mindflow_backend.schemas.orchestration.planning import PlanningDecision
    
    decision = PlanningDecision(
        requires_planning=True,
        confidence=0.9,
        reasoning="Test",
        estimated_subtasks=3,
        complexity_factors=["test"],
    )
    
    # Different cases and whitespace
    cache.set("  Test Message  ", decision)
    
    # Should find with different formatting
    cached1 = cache.get("test message")
    cached2 = cache.get("TEST MESSAGE")
    cached3 = cache.get("  test   message  ")
    
    assert cached1 is not None
    assert cached2 is not None
    assert cached3 is not None
    assert cached1.confidence == 0.9


@pytest.mark.asyncio
async def test_multiple_sessions():
    """Test metrics track multiple sessions correctly."""
    metrics = get_metrics_collector()
    
    # Track decisions for different sessions
    await metrics.track_trigger_decision(
        session_id="session-1",
        trigger_decision=True,
        confidence=0.8,
        latency_ms=800.0,
        method_used="llm",
    )
    
    await metrics.track_trigger_decision(
        session_id="session-2",
        trigger_decision=False,
        confidence=0.3,
        latency_ms=5.0,
        method_used="fallback",
    )
    
    summary = await metrics.get_metrics_summary(timedelta(hours=1))
    
    assert summary["total_decisions"] >= 2
    assert "llm" in summary["method_distribution"]
    assert "fallback" in summary["method_distribution"]
