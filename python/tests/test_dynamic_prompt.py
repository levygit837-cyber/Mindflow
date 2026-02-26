import unittest

from omnimind_agents.dynamic_prompt import build_dynamic_prompt


class DynamicPromptTests(unittest.TestCase):
    def test_returns_system_message_plus_messages(self):
        result = build_dynamic_prompt({"messages": [{"role": "user", "content": "Olá"}]})
        self.assertGreaterEqual(len(result), 2)
        self.assertEqual(result[0]["role"], "system")
        self.assertIn("OmniMind", result[0]["content"])

    def test_includes_filesystem_prompt_when_fs_tool_is_used(self):
        state = {
            "messages": [
                {"role": "user", "content": "leia o arquivo"},
                {
                    "type": "ai",
                    "content": "",
                    "tool_calls": [{"id": "tc-1", "name": "read_file", "args": {"file_path": "/src/index.ts"}}],
                },
            ]
        }
        result = build_dynamic_prompt(state)
        content = result[0]["content"]
        self.assertIn("read_file", content)
        self.assertIn("edit_file", content)

    def test_includes_web_search_prompt_when_search_tool_is_used(self):
        state = {
            "messages": [
                {"role": "user", "content": "pesquise"},
                {
                    "type": "ai",
                    "content": "",
                    "tool_calls": [{"id": "tc-2", "name": "search_web", "args": {"query": "langgraph"}}],
                },
            ]
        }
        result = build_dynamic_prompt(state)
        content = result[0]["content"]
        self.assertIn("search_web", content)


if __name__ == "__main__":
    unittest.main()
