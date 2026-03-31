# Dependency graph analyzer to trace symbol usage across codebase
# FEATURE: Analysis - Blast radius tracer for symbol impact assessment

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.contextplus.core.parser import is_supported_file
from mindflow_backend.contextplus.core.walker import walk_directory, WalkOptions
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameter,
    ToolSchema,
)

_logger = get_logger(__name__)

BLAST_RADIUS_SCHEMA = ToolSchema(
    name="blast_radius",
    description=(
        "Before deleting or modifying code, check the BLAST RADIUS. Traces every file "
        "and line where a specific symbol (function, class, variable) is imported or used. "
        "Prevents orphaned code. Also warns if usage count is low."
    ),
    category="analysis",
    parameters=[
        ToolParameter(
            name="symbol_name",
            type=ParameterType.STRING,
            description="The function, class, or variable name to trace across the codebase.",
            required=True,
        ),
        ToolParameter(
            name="file_context",
            type=ParameterType.STRING,
            description="The file where the symbol is defined. Excludes the definition line from results.",
            required=False,
        ),
    ],
)


def _escape_regex(text: str) -> str:
    """Escape special regex characters."""
    return re.escape(text)


def _is_definition_line(line: str, symbol_name: str) -> bool:
    """Check if a line is a definition of the symbol."""
    patterns = [
        rf"(?:function|class|enum|interface|struct|type|trait|fn|def|func)\s+{_escape_regex(symbol_name)}",
        rf"(?:const|let|var|pub|export)\s+(?:async\s+)?(?:function\s+)?{_escape_regex(symbol_name)}",
    ]
    return any(re.search(p, line) for p in patterns)


async def _get_blast_radius(
    root_dir: str,
    symbol_name: str,
    file_context: str | None = None,
) -> str:
    """Implementation of blast radius analysis."""
    entries = walk_directory(WalkOptions(root_dir=root_dir, depth_limit=0))
    files = [e for e in entries if not e.is_directory and is_supported_file(e.path)]

    usages: list[dict[str, Any]] = []
    symbol_pattern = re.compile(rf"\b{_escape_regex(symbol_name)}\b")

    for file_entry in files:
        try:
            content = Path(file_entry.path).read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            for i, line in enumerate(lines):
                if symbol_pattern.search(line):
                    is_def = (
                        file_context
                        and file_entry.relative_path == file_context
                        and _is_definition_line(line, symbol_name)
                    )
                    if not is_def:
                        usages.append(
                            {
                                "file": file_entry.relative_path,
                                "line": i + 1,
                                "context": line.strip()[:120],
                            }
                        )
        except Exception:
            continue

    if not usages:
        return f'Symbol "{symbol_name}" is not used anywhere in the codebase.'

    by_file: dict[str, list[dict[str, Any]]] = {}
    for u in usages:
        by_file.setdefault(u["file"], []).append(u)

    lines = [f'Blast radius for "{symbol_name}": {len(usages)} usages in {len(by_file)} files\n']

    for file_path, file_usages in sorted(by_file.items()):
        lines.append(f"  {file_path}:")
        for u in file_usages:
            lines.append(f"    L{u['line']}: {u['context']}")

    if len(usages) <= 1:
        lines.append(f"\n⚠ LOW USAGE: This symbol is used only {len(usages)} time(s). Consider inlining if it's under 20 lines.")

    return "\n".join(lines)


class BlastRadiusTool(AsyncToolInterface):
    """Symbol usage tracer for impact analysis."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "blast_radius"
        self.description = BLAST_RADIUS_SCHEMA.description
        self._schema = BLAST_RADIUS_SCHEMA

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        symbol_name = kwargs.get("symbol_name")
        if not symbol_name:
            return self._format_result(success=False, error="symbol_name is required")

        file_context = kwargs.get("file_context")
        root_dir = self.root_dir or "."

        try:
            result = await _get_blast_radius(
                root_dir=root_dir,
                symbol_name=symbol_name,
                file_context=file_context,
            )
            return self._format_result(success=True, result=result)
        except Exception as e:
            _logger.error(f"blast_radius failed: {e}")
            return self._format_result(success=False, error=str(e))