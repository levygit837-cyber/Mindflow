import re
from enum import StrEnum


class NodeCategory(StrEnum):
    LLM_INVOKE = "LLM_INVOKE"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    SUBGRAPH = "SUBGRAPH"
    INTERNAL = "INTERNAL"
    UNKNOWN = "UNKNOWN"


_INTERNAL_PATTERNS = [
    re.compile(r"^__"),
    re.compile(r"Middleware", re.IGNORECASE),
    re.compile(r"\.before_"),
    re.compile(r"\.after_"),
    re.compile(r"^model_request$"),
    re.compile(r"^model_response$"),
    re.compile(r"^patchToolCalls"),
]

_LLM_NODES = {"agent", "model", "llm", "generate", "chat"}
_TOOL_NODES = {"tools", "tool_executor", "tool_node", "action"}


def classify_node(node_name: str) -> NodeCategory:
    if not node_name:
        return NodeCategory.INTERNAL
    if ":" in node_name:
        return NodeCategory.SUBGRAPH

    for pattern in _INTERNAL_PATTERNS:
        if pattern.search(node_name):
            return NodeCategory.INTERNAL

    if node_name in _LLM_NODES:
        return NodeCategory.LLM_INVOKE
    if node_name in _TOOL_NODES:
        return NodeCategory.TOOL_EXECUTION
    return NodeCategory.UNKNOWN


def is_streamable_node(node_name: str) -> bool:
    category = classify_node(node_name)
    return category in {
        NodeCategory.LLM_INVOKE,
        NodeCategory.TOOL_EXECUTION,
        NodeCategory.SUBGRAPH,
        NodeCategory.UNKNOWN,
    }


def get_node_label(node_name: str) -> str:
    if not node_name:
        return "Node"

    if ":" in node_name:
        parent, child = node_name.split(":", 1)
        return f"{_title_case(parent)} › {_title_case(child)}"

    canonical = {
        "agent": "Agent",
        "tools": "Tools",
        "model": "Model",
        "llm": "LLM",
        "generate": "Generate",
        "chat": "Chat",
        "tool_executor": "Tools",
        "tool_node": "Tools",
        "action": "Action",
    }
    return canonical.get(node_name, _title_case(node_name))


def _title_case(value: str) -> str:
    words = value.replace("_", " ").replace("-", " ").strip().split()
    return " ".join(word.capitalize() for word in words)
