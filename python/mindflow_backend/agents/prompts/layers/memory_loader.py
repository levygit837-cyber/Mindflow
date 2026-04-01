"""Memory File Loader — unified loader for MIND.md memory files.

Loads memory files from 4 types (User, Project, Local, Managed) following
the Claude Code CLAUDE.md hierarchy pattern.

Usage:
    loader = MemoryFileLoader()
    files = await loader.load_all("/path/to/project")
    for mf in files:
        print(f"{mf.source}: {mf.content[:100]}")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from mindflow_backend.agents.prompts.layers.memory_types import (
    DEFAULT_SEARCH_PATHS,
    MEMORY_TYPE_HEADERS,
    MEMORY_TYPE_PRIORITY,
    MemoryType,
)

logger = logging.getLogger(__name__)


@dataclass
class MemoryFile:
    """Represents a loaded MIND.md memory file."""

    content: str
    source: MemoryType
    path: str
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_estimate: int = 0

    def __post_init__(self) -> None:
        if self.token_estimate == 0:
            self.token_estimate = self._estimate_tokens(self.content)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimation (~4 chars per token for English, ~2 for CJK)."""
        return max(1, len(text) // 4)

    @property
    def header(self) -> str:
        """Returns the descriptive header for this memory type."""
        return MEMORY_TYPE_HEADERS.get(self.source, "## Memory")


class MemoryFileLoader:
    """Loads MIND.md files from all memory types.

    Follows Claude Code's memory loading pattern:
    1. User Memory:     ~/.mindflow/MIND.md
    2. Project Memory:  ./.mindflow/MIND.md or ./MIND.md
    3. Local Memory:    ./.mindflow/MIND.local.md or ./MIND.local.md
    4. Managed Memory:  ~/.mindflow/managed/MIND.md or /etc/mindflow/MIND.md

    Each type is loaded independently — missing files are silently skipped.
    """

    def __init__(
        self,
        search_paths: dict[MemoryType, list[str]] | None = None,
        max_file_size_kb: int = 50,
        encoding: str = "utf-8",
    ) -> None:
        self._search_paths = search_paths or DEFAULT_SEARCH_PATHS
        self._max_file_size_bytes = max_file_size_kb * 1024
        self._encoding = encoding

    async def load_all(
        self,
        working_dir: str,
        types: Sequence[MemoryType] | None = None,
    ) -> list[MemoryFile]:
        """Load all requested memory types.

        Args:
            working_dir: Base directory for relative path resolution.
            types: Which memory types to load. Defaults to all 4 types.

        Returns:
            List of loaded MemoryFile objects, sorted by priority (highest first).
        """
        enabled_types = list(types) if types else list(MemoryType)
        results: list[MemoryFile] = []

        for memory_type in enabled_types:
            mf = await self.load_by_type(memory_type, working_dir)
            if mf is not None:
                results.append(mf)

        # Sort by priority (highest first) — matches prompt injection order
        results.sort(
            key=lambda f: MEMORY_TYPE_PRIORITY.get(f.source, 0),
            reverse=True,
        )
        return results

    async def load_by_type(
        self,
        memory_type: MemoryType,
        working_dir: str,
    ) -> MemoryFile | None:
        """Load a single memory type by searching its candidate paths.

        Args:
            memory_type: The type of memory to load.
            working_dir: Base directory for relative path resolution.

        Returns:
            MemoryFile if found and readable, None otherwise.
        """
        candidates = self._search_paths.get(memory_type, [])

        for raw_path in candidates:
            resolved = self._resolve_path(raw_path, working_dir)
            if resolved is None:
                continue

            content = self._read_file(resolved)
            if content is not None:
                logger.debug(
                    "Loaded %s memory from %s (%d chars)",
                    memory_type.value,
                    resolved,
                    len(content),
                )
                return MemoryFile(
                    content=content,
                    source=memory_type,
                    path=str(resolved),
                )

        logger.debug("No %s memory file found in candidates: %s", memory_type.value, candidates)
        return None

    def _resolve_path(self, raw_path: str, working_dir: str) -> Path | None:
        """Resolve a path string to an absolute Path.

        Handles:
        - ~ expansion
        - Relative paths (resolved against working_dir)
        - Absolute paths (used as-is)
        """
        try:
            expanded = os.path.expanduser(raw_path)
            path = Path(expanded)

            if path.is_absolute():
                return path

            # Relative path — resolve against working_dir
            return Path(working_dir) / path
        except (OSError, ValueError) as e:
            logger.debug("Failed to resolve path %r: %s", raw_path, e)
            return None

    def _read_file(self, path: Path) -> str | None:
        """Read file content with size and encoding checks."""
        try:
            if not path.is_file():
                return None

            # Check file size
            stat = path.stat()
            if stat.st_size > self._max_file_size_bytes:
                logger.warning(
                    "Memory file %s exceeds max size (%d bytes > %d bytes), skipping",
                    path,
                    stat.st_size,
                    self._max_file_size_bytes,
                )
                return None

            if stat.st_size == 0:
                logger.debug("Memory file %s is empty, skipping", path)
                return None

            return path.read_text(encoding=self._encoding)
        except PermissionError:
            logger.debug("Permission denied reading %s", path)
            return None
        except OSError as e:
            logger.debug("Failed to read %s: %s", path, e)
            return None

    @staticmethod
    def estimate_total_tokens(files: list[MemoryFile]) -> int:
        """Estimate total tokens across all loaded memory files."""
        return sum(f.token_estimate for f in files)