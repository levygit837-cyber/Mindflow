import pytest
from omnimind_backend.orchestrator.complexity import ComplexityScorer

def test_heuristic_scoring():
    scorer = ComplexityScorer()
    
    # Simple message
    simple_score = scorer.calculate_heuristic_score("olá")
    assert simple_score < 0.2
    
    # Complex message with keywords
    complex_msg = "Preciso que você realize uma refatoração em múltiplos arquivos do projeto para implementar a nova arquitetura."
    complex_score = scorer.calculate_heuristic_score(complex_msg)
    assert complex_score >= 0.3
    
    # Very complex with code
    very_complex = (
        "Refatorar o sistema de login. "
        "```python\nprint('hello')\n``` "
        "Implementar suporte a OAuth2 e migrar banco de dados."
    )
    very_complex_score = scorer.calculate_heuristic_score(very_complex)
    assert very_complex_score >= 0.5

def test_should_decompose():
    scorer = ComplexityScorer(threshold=0.65)
    assert scorer.should_decompose(0.7) is True
    assert scorer.should_decompose(0.4) is False


@pytest.mark.asyncio
async def test_get_complexity_score_handles_list_content_from_model(monkeypatch):
    class _Response:
        content = [{"type": "text", "text": "0.90"}]

    class _Model:
        async def ainvoke(self, _prompt):
            return _Response()

    monkeypatch.setattr(
        "omnimind_backend.orchestrator.complexity.get_model_for_provider",
        lambda _provider, _model: _Model(),
    )

    scorer = ComplexityScorer()
    message = "implementar refactor com migration em multiple files"
    h_score = scorer.calculate_heuristic_score(message)
    score = await scorer.get_complexity_score(message, provider="openai", model="stub")

    assert score > h_score
