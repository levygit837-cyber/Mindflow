# Structural tree generator with file headers, symbols, and depth control
# FEATURE: Discovery - Token-aware context tree with symbol ranges

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.contextplus.core.parser import analyze_file, format_symbol, is_supported_file
from mindflow_backend.contextplus.core.walker import FileEntry, walk_directory, WalkOptions
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameter,
    ToolSchema,
)

_logger = get_logger(__name__)

CHARS_PER_TOKEN = 4

CONTEXT_TREE_SCHEMA = ToolSchema(
    name="context_tree",
    description=(
        "Get the structural tree of the project with file headers, function names, "
        "classes, enums, and line ranges. Dynamic token-aware pruning: "
        "Level 2 (deep symbols) -> Level 1 (headers only) -> Level 0 (file names only) "
        "based on project size."
    ),
    category="discovery",
    parameters=[
        ToolParameter(
            name="target_path",
            type=ParameterType.STRING,
            description="Specific directory or file to analyze (relative to project root). Defaults to root.",
            required=False,
        ),
        ToolParameter(
            name="depth_limit",
            type=ParameterType.INTEGER,
            description="How many folder levels deep to scan. Use 1-2 for large projects.",
            required=False,
        ),
        ToolParameter(
            name="include_symbols",
            type=ParameterType.BOOLEAN,
            description="Include function/class/enum names in the tree. Defaults to true.",
            required=False,
            default=True,
        ),
        ToolParameter(
            name="max_tokens",
            type=ParameterType.INTEGER,
            description="Maximum tokens for output. Auto-prunes if exceeded. Default: 20000.",
            required=False,
            default=20000,
        ),
    ],
)


class _TreeNode:
    """Internal tree node representation."""

    def __init__(self, name: str, relative_path: str, is_directory: bool) -> None:
        self.name = name
        self.relative_path = relative_path
        self.is_directory = is_directory
        self.header: str | None = None
        self.symbols: str | None = None
        self.children: list[_TreeNode] = []


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text."""
    return len(text) // CHARS_PER_TOKEN


async def _build_tree(entries: list[FileEntry], include_symbols: bool) -> _TreeNode:
    """Build tree structure from file entries."""
    root = _TreeNode(".", ".", True)
    dir_map: dict[str, _TreeNode] = {".": root}

    sorted_entries = sorted(entries, key=lambda e: (e.depth, e.relative_path))

    for entry in sorted_entries:
        parts = entry.relative_path.split("/")
        parent_path = "/".join(parts[:-1]) if len(parts) > 1 else "."

        parent = dir_map.get(parent_path, root)

        node = _TreeNode(
            name=parts[-1],
            relative_path=entry.relative_path,
            is_directory=entry.is_directory,
        )

        if not entry.is_directory and is_supported_file(entry.path):
            try:
                analysis = await analyze_file(entry.path)
                node.header = analysis.header or None
                if include_symbols and analysis.symbols:
                    node.symbols = "\n".join(format_symbol(s) for s in analysis.symbols)
            except Exception:
                pass

        parent.children.append(node)
        if entry.is_directory:
            dir_map[entry.relative_path] = node

    return root


def _render_tree(node: _TreeNode, indent: int = 0) -> str:
    """Render tree to text format."""
    result = ""
    pad = "  " * indent

    if indent == 0:
        result = f"{node.name}/\n"
    elif node.is_directory:
        result = f"{pad}{node.name}/\n"
    else:
        result = f"{pad}{node.name}"
        if node.header:
            result += f" | {node.header}"
        result += "\n"
        if node.symbols:
            for line in node.symbols.split("\n"):
                result += f"{pad}  {line}\n"

    for child in node.children:
        result += _render_tree(child, indent + 1)
    return result


def _prune_symbols(node: _TreeNode) -> None:
    """Remove symbols from tree (Level 1 pruning)."""
    node.symbols = None
    for child in node.children:
        _prune_symbols(child)


def _prune_headers(node: _TreeNode) -> None:
    """Remove headers and symbols from tree (Level 0 pruning)."""
    node.header = None
    node.symbols = None
    for child in node.children:
        _prune_headers(child)


async def _get_context_tree(
    root_dir: str,
    target_path: str | None = None,
    depth_limit: int | None = None,
    include_symbols: bool = True,
    max_tokens: int = 20000,
) -> str:
    """Implementation of context tree generation."""
    entries = walk_directory(
        WalkOptions(
            root_dir=root_dir,
            target_path=target_path,
            depth_limit=depth_limit,
        )
    )

    tree = await _build_tree(entries, include_symbols)
    rendered = _render_tree(tree)

    if _estimate_tokens(rendered) <= max_tokens:
        return rendered

    _prune_symbols(tree)
    rendered = _render_tree(tree)
    if _estimate_tokens(rendered) <= max_tokens:
        return f"[Level 1: Headers only, symbols pruned to fit {max_tokens} tokens]\n\n{rendered}"

    _prune_headers(tree)
    rendered = _render_tree(tree)
    return f"[Level 0: File names only, project too large for {max_tokens} tokens]\n\n{rendered}"


class ContextTreeTool(AsyncToolInterface):
    """Structural AST tree generator for codebase exploration."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "context_tree"
        self.description = CONTEXT_TREE_SCHEMA.description
        self._schema = CONTEXT_TREE_SCHEMA

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        target_path = kwargs.get("target_path")
        depth_limit = kwargs.get("depth_limit")
        include_symbols = kwargs.get("include_symbols", True)
        max_tokens = kwargs.get("max_tokens", 20000)

        root_dir = self.root_dir or "."

        try:
            result = await _get_context_tree(
                root_dir=root_dir,
                target_path=target_path,
                depth_limit=depth_limit,
                include_symbols=include_symbols,
                max_tokens=max_tokens,
            )
            return self._format_result(success=True, result=result)
        except Exception as e:
            _logger.error(f"context_tree failed: {e}")
            return self._format_result(success=False, error=str(e))