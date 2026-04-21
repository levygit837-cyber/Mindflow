"""MindFlow Agent System.

Keep package imports lightweight so tests and tooling can load specialist modules
without booting the full context/memory stack.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AgentPersonality",
    "AgentRegistry",
    "BaseAgent",
    "context",
    "specialists",
    "get_agent",
    "get_agent_context_retriever",
    "get_registry",
    "get_specialist_selector",
    "register_all_specialists",
]

_LAZY_ATTRS: dict[str, tuple[str, str | None]] = {
    "context": ("mindflow_backend.agents.context", None),
    "specialists": ("mindflow_backend.agents.specialists", None),
    "AgentPersonality": ("mindflow_backend.agents._base", "AgentPersonality"),
    "BaseAgent": ("mindflow_backend.agents._base", "BaseAgent"),
    "AgentRegistry": ("mindflow_backend.agents._registry", "AgentRegistry"),
    "get_agent": ("mindflow_backend.agents._registry", "get_agent"),
    "get_registry": ("mindflow_backend.agents._registry", "get_registry"),
    "register_all_specialists": ("mindflow_backend.agents._registry", "register_all_specialists"),
    "get_agent_context_retriever": (
        "mindflow_backend.agents.context",
        "get_agent_context_retriever",
    ),
    "get_specialist_selector": ("mindflow_backend.agents.specialists", "get_specialist_selector"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _LAZY_ATTRS[name]
    except KeyError as exc:  # pragma: no cover - Python fallback path
        raise AttributeError(name) from exc
    module = import_module(module_name)
    return module if attr_name is None else getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
