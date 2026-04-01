"""Memory file layer — loads CLAUDE.md / MINDFLOW.md files.

Equivalent to Claude Code's memory file loading.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from mindflow_backend.agents.prompts.assembler import AssemblyContext

logger = logging.getLogger(__name__)


class MemoryFileLayer:
    """Carrega arquivos de memória do projeto e do usuário."""

    name = "memory"
    priority = 85  # Alta prioridade

    async def render(self, context: AssemblyContext) -> str | None:
        working_dir = context.working_directory or os.getcwd()
        content_parts: list[str] = []

        # Project memory: .mindflow/CLAUDE.md or CLAUDE.md
        project_memory = self._find_project_memory(working_dir)
        if project_memory:
            content_parts.append(project_memory)

        # User global memory: ~/.mindflow/CLAUDE.md
        user_memory = self._find_user_memory()
        if user_memory:
            content_parts.append(user_memory)

        if not content_parts:
            return None

        return "## Project Memory\n\n" + "\n\n".join(content_parts)

    def _find_project_memory(self, working_dir: str) -> str | None:
        """Find project-level memory files."""
        candidates = [
            Path(working_dir) / ".mindflow" / "CLAUDE.md",
            Path(working_dir) / "CLAUDE.md",
            Path(working_dir) / ".claude" / "CLAUDE.md",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except Exception:
                    logger.debug(f"Failed to read memory file: {path}", exc_info=True)
                    continue
        return None

    def _find_user_memory(self) -> str | None:
        """Find user-level memory files."""
        home = Path.home()
        candidates = [
            home / ".mindflow" / "CLAUDE.md",
            home / ".claude" / "CLAUDE.md",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except Exception:
                    logger.debug(f"Failed to read user memory file: {path}", exc_info=True)
                    continue
        return None