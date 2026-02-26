import unittest

from omnimind_agents.node_registry import classify_node, get_node_label, is_streamable_node
from omnimind_agents.types import NodeCategory


class NodeRegistryTests(unittest.TestCase):
    def test_classifies_agent_as_llm(self):
        self.assertEqual(classify_node("agent"), NodeCategory.LLM_INVOKE)

    def test_classifies_tools_as_tool_execution(self):
        self.assertEqual(classify_node("tools"), NodeCategory.TOOL_EXECUTION)

    def test_classifies_internal_nodes(self):
        self.assertEqual(classify_node("patchToolCallsMiddleware.before_agent"), NodeCategory.INTERNAL)
        self.assertEqual(classify_node("__start__"), NodeCategory.INTERNAL)

    def test_classifies_subgraph_nodes(self):
        self.assertEqual(classify_node("coder:agent"), NodeCategory.SUBGRAPH)

    def test_labels(self):
        self.assertEqual(get_node_label("agent"), "Agent")
        self.assertEqual(get_node_label("coder:agent"), "Coder › Agent")

    def test_is_streamable(self):
        self.assertFalse(is_streamable_node("__start__"))
        self.assertTrue(is_streamable_node("agent"))


if __name__ == "__main__":
    unittest.main()
