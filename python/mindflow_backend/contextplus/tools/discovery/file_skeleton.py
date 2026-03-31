# Detailed function signature extractor without reading full file bodies
# FEATURE: Discovery - File skeleton with signatures, params, and return types

from __future__ import annotations

from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.contextplus.core.parser import (
    FileAnalysis,
    analyze_file,
    is_supported_file,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameter,
    ToolSchema,
)

_logger = get_logger(__name__)

FILE_SKELETON_SCHEMA = ToolSchema(
    name="file_skeleton",
    description=(
        "Get detailed function signatures, class methods, and type definitions of a "
        "specific file WITHOUT reading the full body. Shows the API surface: function "
        "names, parameters, return types, and line ranges. Perfect for understanding "
        "how to use code without loading it all."
    ),
    category="discovery",
    parameters=[
        ToolParameter(
            name="file_path",
            type=ParameterType.STRING,
            description="Path to the file to inspect (relative to project root).",
            required=True,
        ),
    ],
)


def _format_line_range(line: int, end_line: int) -> str:
    """Format line range for display."""
    return f"L{line}-L{end_line}" if end_line > line else f"L{line}"


def _format_signature_block(analysis: FileAnalysis) -> str:
    """Format analysis into signature block."""
    lines: list[str] = []

    if analysis.header:
        lines.append(f"// {analysis.header}")
        lines.append("")

    for sym in analysis.symbols:
        line_range = _format_line_range(sym.line, sym.end_line)
        lines.append(f"[{sym.kind.value}] {line_range} {sym.signature};")
        for child in sym.children:
            child_range = _format_line_range(child.line, child.end_line)
            lines.append(f"  [{child.kind.value}] {child_range} {child.signature};")
        if sym.children:
            lines.append("")

    return "\n".join(lines)


async def _get_file_skeleton(root_dir: str, file_path: str) -> str:
    """Implementation of file skeleton extraction."""
    full_path = str(Path(root_dir) / file_path)

    if not is_supported_file(full_path):
        try:
            content = Path(full_path).read_text(encoding="utf-8", errors="replace")
            preview = "\n".join(content.splitlines()[:20])
            return f"[Unsupported language, showing first 20 lines]\n\n{preview}"
        except Exception:
            return f"[Could not read file: {file_path}]"

    analysis = await analyze_file(full_path)

    if not analysis.symbols:
        try:
            content = Path(full_path).read_text(encoding="utf-8", errors="replace")
            preview = "\n".join(content.splitlines()[:30])
            return f"[No symbols detected, showing first 30 lines]\n\n{preview}"
        except Exception:
            return f"[No symbols detected in: {file_path}]"

    return "\n".join([
        f"File: {file_path} ({analysis.line_count} lines)",
        f"Symbols: {len(analysis.symbols)} top-level definitions",
        "",
        _format_signature_block(analysis),
    ])


class FileSkeletonTool(AsyncToolInterface):
    """File signature extractor for API surface inspection."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "file_skeleton"
        self.description = FILE_SKELETON_SCHEMA.description
        self._schema = FILE_SKELETON_SCHEMA

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        file_path = kwargs.get("file_path")
        if not file_path:
            return self._format_result(success=False, error="file_path is required")

        root_dir = self.root_dir or "."

        try:
            result = await _get_file_skeleton(root_dir, file_path)
            return self._format_result(success=True, result=result)
        except Exception as e:
            _logger.error(f"file_skeleton failed: {e}")
            return self._format_result(success=False, error=str(e))