import json
import unittest

from omnimind_agents.chat_stream_normalizer import create_agent_chat_stream_normalizer


def collect_events(provider: str, items: list):
    events = []

    def emit(event_type, data, mode, meta=None):
        events.append({"type": event_type, "data": data, "mode": mode, "meta": meta or {}})

    normalizer = create_agent_chat_stream_normalizer(provider=provider, emit=emit)
    for item in items:
        normalizer.process(item)
    normalizer.flush()
    return events


class ChatStreamNormalizerTests(unittest.TestCase):
    def test_streams_anthropic_thought_and_response(self):
        events = collect_events(
            "anthropic",
            [
                [
                    ["root", "agent"],
                    "messages",
                    [
                        {
                            "id": "run-1",
                            "type": "ai",
                            "content": [
                                {"type": "thinking", "thinking": "analisando..."},
                                {"type": "text", "text": "Resposta final"},
                            ],
                        },
                        {"langgraph_node": "agent", "run_id": "run-1"},
                    ],
                ]
            ],
        )
        self.assertTrue(any(e["type"] == "thought" and "analisando" in e["data"] for e in events))
        self.assertTrue(any(e["type"] == "response" and "Resposta final" in e["data"] for e in events))

    def test_splits_gemini_think_tags(self):
        events = collect_events(
            "vertexai",
            [
                [
                    ["root", "agent"],
                    "messages",
                    [
                        {
                            "id": "vertex-run-1",
                            "type": "ai",
                            "content": "<think>pensando em passos</think>Resposta pronta",
                        },
                        {"langgraph_node": "agent", "run_id": "vertex-run-1"},
                    ],
                ]
            ],
        )
        thoughts = "".join(e["data"] for e in events if e["type"] == "thought")
        responses = "".join(e["data"] for e in events if e["type"] == "response")
        self.assertIn("pensando em passos", thoughts)
        self.assertIn("Resposta pronta", responses)

    def test_updates_fallback_response(self):
        events = collect_events(
            "openai",
            [
                [
                    ["root", "agent"],
                    "updates",
                    {
                        "agent": {
                            "messages": [
                                {
                                    "id": "ai-update-1",
                                    "type": "ai",
                                    "content": "Fallback output from updates",
                                }
                            ]
                        }
                    },
                ]
            ],
        )
        self.assertTrue(any(e["type"] == "agent_step" for e in events))
        self.assertTrue(any(e["type"] == "response" and "Fallback output" in e["data"] for e in events))

    def test_correlates_tool_call_and_result(self):
        events = collect_events(
            "anthropic",
            [
                [
                    ["root", "agent"],
                    "updates",
                    {
                        "agent": {
                            "messages": [
                                {
                                    "id": "ai-tools-1",
                                    "type": "ai",
                                    "tool_calls": [
                                        {"id": "tc-1", "name": "read_note", "args": {"noteId": "n-1"}}
                                    ],
                                }
                            ]
                        }
                    },
                ],
                [
                    ["root", "tools"],
                    "updates",
                    {
                        "tools": {
                            "messages": [
                                {
                                    "id": "tool-msg-1",
                                    "type": "tool",
                                    "tool_call_id": "tc-1",
                                    "content": "{\"ok\":true}",
                                }
                            ]
                        }
                    },
                ],
            ],
        )

        tool_call = next((e for e in events if e["type"] == "tool_call"), None)
        tool_result = next((e for e in events if e["type"] == "tool_result"), None)
        self.assertIsNotNone(tool_call)
        self.assertIsNotNone(tool_result)
        self.assertIn("read_note", tool_call["data"])
        self.assertIn("read_note", tool_result["data"])

    def test_think_tokens_stream_token_by_token(self):
        emitted = []

        def emit(event_type, data, mode, meta=None):
            emitted.append({"type": event_type, "data": data})

        normalizer = create_agent_chat_stream_normalizer(provider="vertexai", emit=emit)
        tokens = [
            "<",
            "t",
            "h",
            "i",
            "n",
            "k",
            ">",
            "p",
            "e",
            "n",
            "s",
            "a",
            "<",
            "/",
            "t",
            "h",
            "i",
            "n",
            "k",
            ">",
            "o",
            "k",
        ]
        for token in tokens:
            normalizer.process([token, {"langgraph_node": "agent"}])
        normalizer.flush()

        thought_events = [e for e in emitted if e["type"] == "thought"]
        response_events = [e for e in emitted if e["type"] == "response"]

        self.assertGreater(len(thought_events), 0)
        self.assertEqual("".join(e["data"] for e in thought_events), "pensa")
        self.assertEqual("".join(e["data"] for e in response_events), "ok")


if __name__ == "__main__":
    unittest.main()
