"""PromptAssembler — pipeline multi-camada de montagem de system prompt.

Inspired by Claude Code's buildEffectiveSystemPrompt():
- Camada 1: Base (Preamble + Personality + Persistence)
- Camada 2: Tool Descriptions (via ToolPromptInjector)
- Camada 3: Environment Context (datetime, OS, shell, CWD)
- Camada 4: Git Context (branch, staged files)
- Camada 5: Memory/MCP Context
- Camada 6: Additional Instructions
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mindflow_backend.agents._base import BaseAgent

logger = logging.getLogger(__name__)


@runtime_checkable
class PromptLayer(Protocol):
    """Protocol for prompt layers."""
    name: str
    priority: int

    async def render(self, context: "AssemblyContext") -> str | None: ...


@dataclass
class AssemblyContext:
    """Context passed to all layers during assembly."""
    agent: "BaseAgent | None" = None
    working_directory: str | None = None
    query: str | None = None
    mcp_clients: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class PromptAssembler:
    """Pipeline multi-camada de montagem de system prompt."""

    def __init__(self) -> None:
        self._layers: list[PromptLayer] = []

    def add_layer(self, layer: PromptLayer) -> "PromptAssembler":
        """Adiciona camada ao pipeline (builder pattern)."""
        self._layers.append(layer)
        self._layers.sort(key=lambda l: -l.priority)
        return self

    async def assemble(self, context: AssemblyContext | None = None) -> str:
        """Monta o prompt final com todas as camadas."""
        ctx = context or AssemblyContext()
        parts: list[str] = []

        for layer in self._layers:
            try:
                result = await layer.render(ctx)
                if result:
                    parts.append(result)
            except Exception:
                # Log but don't fail the entire assembly
                logger.warning(
                    f"Layer '{layer.name}' failed during assembly",
                    exc_info=True,
                )

        return "\n\n".join(parts)

    def assemble_sync(self, context: AssemblyContext | None = None) -> str:
        """Versão síncrona para backward compatibility."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.assemble(context))
        # If already in an event loop, use a task
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                lambda: asyncio.run(self.assemble(context))
            ).result()