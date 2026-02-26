from __future__ import annotations

import re

from .types import NodeCategory

INTERNAL_NODE_PATTERNS = [
    re.compile(r"^__"),
    re.compile(r"Middleware", re.IGNORECASE),
    re.compile(r"\.before_"),
    re.compile(r"\.after_"),
    re.compile(r"^model_request$"),
    re.compile(r"^model_response$"),
    re.compile(r"^patchToolCalls"),
]

LLM_NODES = {"agent", "model", "llm", "generate", "chat"}
TOOL_NODES = {"tools", "tool_executor", "tool_node", "action"}


def classify_node(node_name: str) -> NodeCategory:
    if not node_name:
        return NodeCategory.INTERNAL

    if ":" in node_name:
        return NodeCategory.SUBGRAPH

    for pattern in INTERNAL_NODE_PATTERNS:
        if pattern.search(node_name):
            return NodeCategory.INTERNAL

    if node_name in LLM_NODES:
        return NodeCategory.LLM_INVOKE
    if node_name in TOOL_NODES:
        return NodeCategory.TOOL_EXECUTION

    return NodeCategory.UNKNOWN


def title_case(value: str) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[_-]+", " ", value).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return re.sub(r"\b\w", lambda m: m.group(0).upper(), normalized)


def get_node_label(node_name: str) -> str:
    if not node_name:
        return "Node"

    if ":" in node_name:
        parent, child = node_name.split(":", 1)
        return f"{title_case(parent)} › {title_case(child)}"

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
    return canonical.get(node_name, title_case(node_name))


def is_streamable_node(node_name: str) -> bool:
    category = classify_node(node_name)
    return category in {
        NodeCategory.LLM_INVOKE,
        NodeCategory.TOOL_EXECUTION,
        NodeCategory.SUBGRAPH,
        NodeCategory.UNKNOWN,
    }
