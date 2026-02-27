from omnimind_backend.agents.node_registry import NodeCategory, classify_node, get_node_label, is_streamable_node


def test_classify_llm_node() -> None:
    assert classify_node("agent") == NodeCategory.LLM_INVOKE


def test_classify_subgraph() -> None:
    assert classify_node("coder:agent") == NodeCategory.SUBGRAPH


def test_internal_node_not_streamable() -> None:
    assert classify_node("__start__") == NodeCategory.INTERNAL
    assert is_streamable_node("__start__") is False


def test_label_generation() -> None:
    assert get_node_label("coder:tool_node") == "Coder › Tool Node"
