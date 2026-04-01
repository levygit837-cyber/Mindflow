"""Memory file layer — loads MIND.md files from 4 memory types.

Inspired by Claude Code's CLAUDE.md hierarchy:
- User Memory:     ~/.mindflow/MIND.md (personal preferences)
- Project Memory:  ./.mindflow/MIND.md or ./MIND.md (versioned instructions)
- Local Memory:    ./.mindflow/MIND.local.md or ./MIND.local.md (gitignored)
- Managed Memory:  ~/.mindflow/managed/MIND.md (enterprise/admin)

Legacy support: Still loads CLAUDE.md files as fallback for backward compatibility.
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

from mindflow_backend.agents.prompts.assembler import AssemblyContext
from mindflow_backend.agents.prompts.layers.memory_loader import MemoryFile, MemoryFileLoader
from mindflow_backend.agents.prompts.layers.memory_types import (
    MEMORY_TYPE_HEADERS,
    MemoryType,
)

logger = logging.getLogger(__name__)


class MemoryFileLayer:
    """Carrega arquivos MIND.md com hierarquia de 4 tipos de memória.

    Ordem de injeção no prompt (por prioridade):
    1. Managed Memory (enterprise) — prioridade 95
    2. User Memory (pessoal) — prioridade 90
    3. Project Memory (projeto) — prioridade 85
    4. Local Memory (local) — prioridade 82
    """

    name = "memory"
    priority = 85  # Alta prioridade — injeta após base e antes de environment

    def __init__(
        self,
        enabled_types: Sequence[MemoryType] | None = None,
        include_headers: bool = True,
    ) -> None:
        """Initialize the memory file layer.

        Args:
            enabled_types: Which memory types to load. Defaults to all 4 types.
            include_headers: Whether to include descriptive headers in the prompt.
        """
        self._loader = MemoryFileLoader()
        self._enabled_types = list(enabled_types) if enabled_types else list(MemoryType)
        self._include_headers = include_headers

    async def render(self, context: AssemblyContext) -> str | None:
        working_dir = context.working_directory or os.getcwd()

        # Load all enabled memory types
        memory_files = await self._loader.load_all(
            working_dir,
            types=self._enabled_types,
        )

        if not memory_files:
            return None

        # Build prompt sections with headers
        parts: list[str] = []
        for mf in memory_files:
            if self._include_headers:
                parts.append(f"{mf.header}\n\n{mf.content}")
            else:
                parts.append(mf.content)

        # Log loaded memory for debugging
        total_tokens = MemoryFileLoader.estimate_total_tokens(memory_files)
        loaded_types = [mf.source.value for mf in memory_files]
        logger.debug(
            "Loaded memory files: %s (~%d tokens)",
            loaded_types,
            total_tokens,
        )

        return "\n\n---\n\n".join(parts)

    def get_loaded_types(self) -> list[MemoryType]:
        """Returns the list of enabled memory types."""
        return list(self._enabled_types)
