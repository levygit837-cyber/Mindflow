from __future__ import annotations

from typing import Any, Dict, List, Set

from .prompts.base import BASE_PROMPT
from .prompts.tools.filesystem import FILESYSTEM_PROMPT
from .prompts.tools.shell import SHELL_PROMPT
from .prompts.tools.task_planning import TASK_PLANNING_PROMPT
from .prompts.tools.web_search import WEB_SEARCH_PROMPT

TOOL_PROMPT_MODULES = [
    {
        "tool_names": ["ls", "read_file", "write_file", "edit_file", "glob", "grep"],
        "prompt": FILESYSTEM_PROMPT,
    },
    {"tool_names": ["search_web"], "prompt": WEB_SEARCH_PROMPT},
    {"tool_names": ["write_todos"], "prompt": TASK_PLANNING_PROMPT},
    {"tool_names": ["execute"], "prompt": SHELL_PROMPT},
]


def extract_recent_tool_names(messages: List[Dict[str, Any]]) -> Set[str]:
    names: Set[str] = set()

    for msg in messages:
        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                if isinstance(tool_call, dict) and tool_call.get("name"):
                    names.add(str(tool_call["name"]))

        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_use"
                    and block.get("name")
                ):
                    names.add(str(block["name"]))

    return names


def build_static_system_prompt() -> str:
    return "\n\n".join(
        [BASE_PROMPT, FILESYSTEM_PROMPT, WEB_SEARCH_PROMPT, TASK_PLANNING_PROMPT, SHELL_PROMPT]
    )


def build_dynamic_prompt(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages = state.get("messages", [])
    used_tools = extract_recent_tool_names(messages)

    sections = [BASE_PROMPT]
    added_prompts = set()
    include_all = len(used_tools) == 0

    for module in TOOL_PROMPT_MODULES:
        is_relevant = include_all or any(name in used_tools for name in module["tool_names"])
        if is_relevant and module["prompt"] not in added_prompts:
            sections.append(module["prompt"])
            added_prompts.add(module["prompt"])

    return [{"role": "system", "content": "\n\n".join(sections)}, *messages]
