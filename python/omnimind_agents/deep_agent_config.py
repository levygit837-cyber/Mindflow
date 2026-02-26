from __future__ import annotations

import os
from typing import Any, Dict

from .dynamic_prompt import build_static_system_prompt


def create_omnimind_deep_agent(model: Any, system_prompt: str | None = None) -> Any:
    """Creates the Python DeepAgent using deepagents package.

    This mirrors the TS setup and intentionally keeps the backend setup small.
    """
    try:
        from deepagents import CompositeBackend, FilesystemBackend, StateBackend, create_deep_agent
    except ImportError as exc:
        raise RuntimeError("Missing dependency: pip install deepagents") from exc

    prompt = system_prompt or build_static_system_prompt()

    backend = CompositeBackend(
        FilesystemBackend(root_dir=os.getcwd()),
        {
            "/memories/": StateBackend(state={}, store=None),
        },
    )

    return create_deep_agent(
        model=model,
        system_prompt=prompt,
        name="omnimind-agent",
        tools=[],
        backend=backend,
    )
