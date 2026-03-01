from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from omnimind_backend.agents.tools.search_web import search_web
from omnimind_backend.infra.config import get_settings


@dataclass
class DeepAgentConfig:
    model: Any
    system_prompt: str
    root_dir: str | None = None


async def search_web_tool(query: str) -> str:
    return await search_web(query)


def create_omnimind_deep_agent(config: DeepAgentConfig):
    """Create a DeepAgents agent with filesystem backend + memory scaffolding.

    This is the Python equivalent to the previous TypeScript `createOmniMindDeepAgent` factory.
    """

    settings = get_settings()
    root_dir = config.root_dir or str(Path.cwd())

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
    except Exception as exc:  # pragma: no cover - import guard for environments w/o deepagents
        raise RuntimeError(
            "deepagents is not available. Install dependencies from python/pyproject.toml"
        ) from exc

    backend = FilesystemBackend(root_dir=root_dir)

    # memory files are injected by middleware when available
    memory_paths = [
        str(Path(root_dir) / "AGENTS.md"),
        str(Path(root_dir) / ".omnimind" / "memory.md"),
    ]

    return create_deep_agent(
        model=config.model,
        system_prompt=config.system_prompt,
        tools=[search_web_tool],
        backend=backend,
        memory=[p for p in memory_paths if Path(p).exists()],
        metadata={
            "name": "omnimind-agent",
            "default_provider": settings.default_provider,
        },
    )
