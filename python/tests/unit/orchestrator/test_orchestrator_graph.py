"""Tests for the orchestrator graph."""

from types import SimpleNamespace

import pytest

from mindflow_backend.orchestrator.graph import build_orchestrator_graph, route_node
from mindflow_backend.schemas.orchestrator import ThinkingMode



def test_build_orchestrator_graph_returns_compiled_graph() -> None:
    graph = build_orchestrator_graph()
    
    # LangGraph's CompiledGraph inherits from Runnable
    assert hasattr(graph, "ainvoke")
    assert hasattr(graph, "invoke")
    
    # Check the nodes
    nodes = list(graph.get_graph().nodes.keys())
    assert "route" in nodes
    assert "execute" in nodes
    assert "respond" in nodes
    assert "__start__" in nodes  # Built-in starting node


@pytest.mark.asyncio
async def test_route_node_keeps_normal_thinking_when_decomposition_disabled(monkeypatch) -> None:
    class _HighComplexityScorer:
        async def get_complexity_score(self, message, provider=None, model=None):  # noqa: ANN001
            return 0.95

        def should_decompose(self, score: float) -> bool:
            return True

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.complexity.ComplexityScorer",
        _HighComplexityScorer,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.graph.get_settings",
        lambda: SimpleNamespace(enable_decomposition_thinking=False),
    )

    result = await route_node({"message": "Faça uma refatoração complexa em múltiplos módulos"})

    assert result["decision"].thinking_mode == ThinkingMode.NORMAL
