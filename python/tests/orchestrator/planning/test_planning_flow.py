"""Tests for planning flow integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from mindflow_backend.orchestrator.planning_flow import (
    should_trigger_planning,
    should_trigger_planning_v2,
    should_trigger_planning_hybrid,
)
from mindflow_backend.schemas.orchestration.planning import PlanningDecision


@pytest.fixture
def mock_planning_service(monkeypatch):
    """Mock planning service."""
    service = MagicMock()
    service.get_session_plans = AsyncMock(return_value=[])
    
    def get_service():
        return service
    
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.planning_flow.get_planning_service",
        get_service
    )
    return service


@pytest.mark.asyncio
async def test_legacy_trigger_with_keywords(mock_planning_service):
    """Test legacy keyword-based trigger."""
    result = await should_trigger_planning(
        message="Implementar sistema de autenticação",
        complexity_score=0.5,
        session_context={"session_id": "test-123"},
    )
    
    assert result is True


@pytest.mark.asyncio
async def test_legacy_trigger_with_high_complexity(mock_planning_service):
    """Test legacy trigger with high complexity score."""
    result = await should_trigger_planning(
        message="Fazer algo simples",
        complexity_score=0.7,
        session_context={"session_id": "test-123"},
    )
    
    assert result is True


@pytest.mark.asyncio
async def test_legacy_trigger_no_match(mock_planning_service):
    """Test legacy trigger with no keyword match."""
    result = await should_trigger_planning(
        message="Como funciona isso?",
        complexity_score=0.3,
        session_context={"session_id": "test-123"},
    )
    
    assert result is False


@pytest.mark.asyncio
async def test_v2_trigger_with_llm(mock_planning_service, monkeypatch):
    """Test v2 trigger with LLM analysis."""
    
    # Mock analyzer
    mock_decision = PlanningDecision(
        requires_planning=True,
        confidence=0.85,
        reasoning="Multi-step implementation",
        estimated_subtasks=5,
        complexity_factors=["multi-file", "security"],
    )
    
    mock_analyzer = MagicMock()
    mock_analyzer.should_trigger_planning = AsyncMock(return_value=mock_decision)
    
    def get_analyzer():
        return mock_analyzer
    
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.planning_flow.get_planning_analyzer",
        get_analyzer
    )
    
    # Mock event dispatch
    async def mock_dispatch(*args, **kwargs):
        pass
    
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.planning_flow.adispatch_custom_event",
        mock_dispatch
    )
    
    should_trigger, decision = await should_trigger_planning_v2(
        message="Implementar sistema completo",
        session_context={"session_id": "test-123"},
    )
    
    assert should_trigger is True
    assert decision.confidence == 0.85
    assert decision.estimated_subtasks == 5


@pytest.mark.asyncio
async def test_v2_trigger_with_active_plan(monkeypatch):
    """Test v2 trigger when active plan exists."""
    
    # Mock planning service with active plan
    from mindflow_backend.schemas.orchestration.planning import PlanStatus, PlanDocument
    
    active_plan = PlanDocument(
        plan_id="plan-123",
        session_id="test-123",
        goal="Test goal",
        status=PlanStatus.IN_EXECUTION,
        tasks=[],
    )
    
    service = MagicMock()
    service.get_session_plans = AsyncMock(return_value=[active_plan])
    
    def get_service():
        return service
    
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.planning_flow.get_planning_service",
        get_service
    )
    
    should_trigger, decision = await should_trigger_planning_v2(
        message="Implementar algo",
        session_context={"session_id": "test-123"},
    )
    
    assert should_trigger is False
    assert "active_plan_exists" in decision.complexity_factors


@pytest.mark.asyncio
async def test_hybrid_trigger_with_flag_enabled(mock_planning_service, monkeypatch):
    """Test hybrid trigger with LLM flag enabled."""
    
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.enable_llm_planning_trigger = True
    
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.planning_flow.get_settings",
        lambda: mock_settings
    )
    
    # Mock v2 trigger
    async def mock_v2(*args, **kwargs):
        decision = PlanningDecision(
            requires_planning=True,
            confidence=0.9,
            reasoning="LLM analysis",
            estimated_subtasks=4,
            complexity_factors=["multi-step"],
        )
        return True, decision
    
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.planning_flow.should_trigger_planning_v2",
        mock_v2
    )
    
    result = await should_trigger_planning_hybrid(
        message="Implementar feature",
        complexity_score=0.5,
        session_context={"session_id": "test-123"},
    )
    
    assert result is True


@pytest.mark.asyncio
async def test_hybrid_trigger_with_flag_disabled(mock_planning_service, monkeypatch):
    """Test hybrid trigger with LLM flag disabled (uses legacy)."""
    
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.enable_llm_planning_trigger = False
    
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.planning_flow.get_settings",
        lambda: mock_settings
    )
    
    result = await should_trigger_planning_hybrid(
        message="Implementar sistema",
        complexity_score=0.5,
        session_context={"session_id": "test-123"},
    )
    
    # Should use legacy keyword matching
    assert result is True
