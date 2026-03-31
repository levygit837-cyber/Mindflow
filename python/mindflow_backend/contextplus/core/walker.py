# Gitignore-aware recursive directory walker with depth control
# FEATURE: Core directory traversal respecting project ignore patterns

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

ALWAYS_IGNORE = frozenset(
    [
        "node_modules",
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".DS_Store",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",
        ".mcp_data",
        ".mcp-shadow-history",
        ".mindflow_contextplus",
        "coverage",
        ".cache",
        ".turbo",
        ".parcel-cache",
    ]
)


@dataclass
class FileEntry:
    """A single file or directory entry from directory traversal."""

    path: str
    relative_path: str
    is_directory: bool
    depth: int


@dataclass
class WalkOptions:
    """Options for directory walking."""

    root_dir: str
    target_path: str | None = None
    depth_limit: int | None = None


def _load_ignore_patterns(root_dir: str) -> list[str]:
    """Load .gitignore patterns from root directory."""
    gitignore_path = Path(root_dir) / ".gitignore"
    patterns: list[str] = []
    try:
        if gitignore_path.exists():
            for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
    except Exception:
        pass
    return patterns


def _is_ignored(rel_path: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any ignore pattern."""
    for pattern in patterns:
        if pattern.endswith("/"):
            if rel_path.startswith(pattern[:-1] + "/") or rel_path == pattern[:-1]:
                return True
        elif pattern.startswith("*."):
            ext = pattern[1:]
            if rel_path.endswith(ext):
                return True
        elif rel_path == pattern or rel_path.startswith(pattern + "/"):
            return True
    return False


def _walk_recursive(
    current_dir: str,
    root_dir: str,
    ignore_patterns: list[str],
    depth: int,
    max_depth: int,
    results: list[FileEntry],
) -> None:
    """Recursively walk directory tree."""
    if max_depth > 0 and depth > max_depth:
        return

    try:
        entries = sorted(os.scandir(current_dir), key=lambda e: e.name)
    except (PermissionError, OSError):
        return

    for entry in entries:
        if ALWAYS_IGNORE & {entry.name}:
            continue
        if entry.name.startswith("."):
            continue

        full_path = entry.path
        rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")

        if _is_ignored(rel_path, ignore_patterns):
            continue

        is_dir = entry.is_dir(follow_symlinks=False)
        results.append(
            FileEntry(
                path=full_path,
                relative_path=rel_path,
                is_directory=is_dir,
                depth=depth,
            )
        )

        if is_dir:
            _walk_recursive(full_path, root_dir, ignore_patterns, depth + 1, max_depth, results)


def walk_directory(options: WalkOptions) -> list[FileEntry]:
    """Walk directory tree with gitignore support and depth control.

    Args:
        options: Walk options including root_dir, target_path, and depth_limit

    Returns:
        List of FileEntry objects for all discovered files and directories
    """
    root_dir = os.path.realpath(options.root_dir)
    start_dir = os.path.realpath(os.path.join(root_dir, options.target_path)) if options.target_path else root_dir

    if not os.path.isdir(start_dir):
        return []

    ignore_patterns = _load_ignore_patterns(root_dir)
    results: list[FileEntry] = []
    _walk_recursive(start_dir, root_dir, ignore_patterns, 0, options.depth_limit or 0, results)
    return results


def group_by_directory(entries: list[FileEntry]) -> dict[str, list[FileEntry]]:
    """Group file entries by their parent directory."""
    groups: dict[str, list[FileEntry]] = {}
    for entry in entries:
        dir_path = os.path.dirname(entry.relative_path) if "/" in entry.relative_path else "."
        if dir_path not in groups:
            groups[dir_path] = []
        groups[dir_path].append(entry)
    return groups