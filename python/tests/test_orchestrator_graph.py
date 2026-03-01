"""Tests for the orchestrator graph."""


from omnimind_backend.orchestrator.graph import build_orchestrator_graph


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
