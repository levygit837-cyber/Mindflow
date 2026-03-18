"""Tests for intelligent planning analyzer."""

from __future__ import annotations

import pytest

from mindflow_backend.orchestrator.planning.analyzer import IntelligentPlanningAnalyzer
from mindflow_backend.schemas.orchestration.planning import PlanningAnalysisRequest


@pytest.fixture
def analyzer():
    """Create analyzer instance for testing."""
    return IntelligentPlanningAnalyzer()


@pytest.mark.asyncio
async def test_should_trigger_for_multi_step_implementation(analyzer):
    """Test that multi-step implementation triggers planning."""
    request = PlanningAnalysisRequest(
        message="Implementar sistema completo de autenticação JWT com refresh tokens"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is True
    assert decision.confidence >= 0.7
    assert decision.estimated_subtasks > 0


@pytest.mark.asyncio
async def test_should_not_trigger_for_simple_question(analyzer):
    """Test that simple questions don't trigger planning."""
    request = PlanningAnalysisRequest(
        message="Como funciona o sistema de autenticação?"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is False
    assert decision.confidence >= 0.5


@pytest.mark.asyncio
async def test_should_not_trigger_for_single_file_fix(analyzer):
    """Test that single-file fixes don't trigger planning."""
    request = PlanningAnalysisRequest(
        message="Corrige o bug na função validate_email() do arquivo utils.py"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is False


@pytest.mark.asyncio
async def test_explicit_planning_request(analyzer):
    """Test that explicit planning requests trigger planning."""
    request = PlanningAnalysisRequest(
        message="Crie um plano para migrar o banco de dados de MySQL para PostgreSQL"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is True
    assert decision.confidence >= 0.8


@pytest.mark.asyncio
async def test_multi_file_refactoring(analyzer):
    """Test that multi-file refactoring triggers planning."""
    request = PlanningAnalysisRequest(
        message="Refatorar a camada de serviços e repositórios aplicando padrão Repository"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is True
    assert decision.confidence >= 0.7


@pytest.mark.asyncio
async def test_architecture_design(analyzer):
    """Test that architecture design triggers planning."""
    request = PlanningAnalysisRequest(
        message="Desenhar arquitetura de microserviços para o sistema de pagamentos"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is True
    assert decision.confidence >= 0.7


@pytest.mark.asyncio
async def test_simple_code_formatting(analyzer):
    """Test that simple formatting doesn't trigger planning."""
    request = PlanningAnalysisRequest(
        message="Formata este código seguindo PEP8"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is False


@pytest.mark.asyncio
async def test_greeting_message(analyzer):
    """Test that greetings don't trigger planning."""
    request = PlanningAnalysisRequest(
        message="Olá, como você está?"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is False
    assert decision.confidence >= 0.7


@pytest.mark.asyncio
async def test_research_request(analyzer):
    """Test that simple research doesn't trigger planning."""
    request = PlanningAnalysisRequest(
        message="Pesquisa sobre FastAPI e suas melhores práticas"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is False


@pytest.mark.asyncio
async def test_feature_with_tests(analyzer):
    """Test that feature with tests triggers planning."""
    request = PlanningAnalysisRequest(
        message="Criar feature completa de notificações incluindo backend, frontend e testes"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.requires_planning is True
    assert decision.confidence >= 0.7
    assert decision.estimated_subtasks >= 3


@pytest.mark.asyncio
async def test_fallback_on_llm_failure(analyzer, monkeypatch):
    """Test that fallback works when LLM fails."""
    
    # Mock LLM to raise exception
    async def mock_call_llm(*args, **kwargs):
        raise Exception("LLM unavailable")
    
    monkeypatch.setattr(analyzer, "_call_llm", mock_call_llm)
    
    request = PlanningAnalysisRequest(
        message="Implementar feature X com múltiplos arquivos e componentes"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    # Should use fallback
    assert "fallback" in decision.reasoning.lower()
    assert decision.confidence <= 0.6
    assert "fallback_mode" in decision.complexity_factors


@pytest.mark.asyncio
async def test_structural_features_extraction(analyzer):
    """Test structural feature extraction."""
    message = """
    Implementar sistema de autenticação:
    - Login com JWT
    - Refresh tokens
    - Logout
    
    Arquivos: auth.py, tokens.py, middleware.py
    """
    
    features = analyzer._extract_structural_features(message)
    
    assert features["word_count"] > 10
    assert features["has_list_markers"] is True
    assert features["has_file_paths"] is True
    assert features["has_multiple_sentences"] is True


@pytest.mark.asyncio
async def test_confidence_scoring(analyzer):
    """Test that confidence scores are within valid range."""
    requests = [
        PlanningAnalysisRequest(message="Olá"),
        PlanningAnalysisRequest(message="Implementar sistema completo"),
        PlanningAnalysisRequest(message="Corrige bug"),
    ]
    
    for request in requests:
        decision = await analyzer.should_trigger_planning(request)
        assert 0.0 <= decision.confidence <= 1.0


@pytest.mark.asyncio
async def test_reasoning_provided(analyzer):
    """Test that reasoning is always provided."""
    request = PlanningAnalysisRequest(
        message="Implementar feature X"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    assert decision.reasoning
    assert len(decision.reasoning) > 10


@pytest.mark.asyncio
async def test_complexity_factors_provided(analyzer):
    """Test that complexity factors are provided when planning is needed."""
    request = PlanningAnalysisRequest(
        message="Implementar sistema completo de autenticação com múltiplos arquivos"
    )
    decision = await analyzer.should_trigger_planning(request)
    
    if decision.requires_planning:
        assert len(decision.complexity_factors) > 0
