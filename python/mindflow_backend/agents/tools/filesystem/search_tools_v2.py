"""Search tools v2 - Enhanced with Claude Code standards.

This module implements GlobTool and GrepTool v2 with full integration of:
- Schemas v2 (filesystem_schemas_v2.py)
- Security validators (filesystem_validators.py)
- Permission system (permission_matcher.py)

Matching Claude Code's feature set and security standards.
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.filesystem_schemas_v2 import (
    GlobSearchInput,
    GrepSearchInput,
)
from mindflow_backend.permissions.types import PermissionBehavior
from mindflow_backend.agents.tools.security.filesystem_validators import (
    validate_filesystem_operation,
    validate_path_traversal_filesystem,
)

_logger = get_logger(__name__)


def _resolve_search_path(root_dir: str | None, raw_path: str | None) -> str:
    """Resolve search path relative to root_dir while preserving absolute inputs."""
    path = Path(raw_path or root_dir or os.getcwd())
    if path.is_absolute():
        return str(path.resolve())
    if root_dir:
        return str((Path(root_dir) / path).resolve())
    return str(path.resolve())


# ============================================================================
# GlobTool v2
# ============================================================================

class GlobToolV2(AsyncToolInterface):
    """Enhanced file pattern matching tool matching Claude Code standards.

    Features:
    - Exclude patterns (ignore certain files/dirs)
    - Max depth control (limit recursion)
    - Sort by mtime (most recently modified first)
    - Pagination (head_limit + offset)
    - Security validators integration
    """

    name = "glob_v2"
    description = (
        "Find files matching glob patterns with advanced features: exclude patterns, "
        "max depth, sort by mtime, pagination, and security validation."
    )

    def __init__(self, root_dir: str | None = None):
        """Initialize GlobTool v2.

        Args:
            root_dir: Root directory for sandboxing (workspace root)
        """
        self.root_dir = root_dir

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute glob search with full validation and security checks."""
        # Parse and validate input
        try:
            input_data = GlobSearchInput(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "error_code": "INVALID_INPUT"
            }

        pattern = input_data.pattern
        path = _resolve_search_path(self.root_dir, input_data.path)
        case_sensitive = kwargs.get("case_sensitive", True)

        # Security validation: path traversal
        traversal_decision = validate_path_traversal_filesystem(path, self.root_dir)
        if traversal_decision.behavior in [PermissionBehavior.DENY, PermissionBehavior.ASK]:
            return {
                "success": False,
                "error": traversal_decision.message,
                "error_code": "PATH_TRAVERSAL"
            }

        # Master filesystem validator
        fs_decision = validate_filesystem_operation(
            file_path=path,
            operation="read",
            workspace_root=self.root_dir
        )

        if fs_decision.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": fs_decision.message,
                "error_code": "PERMISSION_DENIED"
            }

        try:
            # Find matching files
            matches = self._find_matches(
                path=path,
                pattern=pattern,
                exclude_patterns=input_data.exclude_patterns,
                max_depth=input_data.max_depth,
                case_sensitive=case_sensitive,
            )

            # Sort by mtime if requested
            if input_data.sort_by_mtime:
                matches = self._sort_by_mtime(matches)

            total_matches = len(matches)

            # Apply pagination
            if input_data.offset > 0:
                matches = matches[input_data.offset:]

            if input_data.head_limit is not None:
                matches = matches[:input_data.head_limit]

            return {
                "success": True,
                "matches": matches,
                "total_matches": total_matches,
                "returned_matches": len(matches),
                "pattern": pattern,
                "path": path,
                "offset": input_data.offset,
                "truncated": input_data.head_limit is not None and len(matches) < (total_matches - input_data.offset)
            }

        except Exception as e:
            _logger.error(f"Error in glob search: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Glob search failed: {e}",
                "error_code": "GLOB_ERROR"
            }

    def _find_matches(
        self,
        path: str,
        pattern: str,
        exclude_patterns: list[str],
        max_depth: int | None,
        case_sensitive: bool
    ) -> list[str]:
        """Find all files matching pattern."""
        matches = []

        # Convert path to Path object
        base_path = Path(path)
        base_depth = len(base_path.parts)

        # Walk directory tree
        for root, dirs, files in os.walk(path):
            current_path = Path(root)
            current_depth = len(current_path.parts) - base_depth

            # Check max depth
            if max_depth is not None:
                if current_depth > max_depth:
                    dirs.clear()
                    continue
                if current_depth >= max_depth:
                    dirs.clear()  # Include this level, but don't recurse deeper

            # Filter directories by exclude patterns
            if exclude_patterns:
                dirs[:] = [
                    d for d in dirs
                    if not self._matches_any_pattern(d, exclude_patterns, case_sensitive)
                ]

            # Check files
            for file in files:
                # Skip if matches exclude pattern
                if exclude_patterns and self._matches_any_pattern(file, exclude_patterns, case_sensitive):
                    continue

                # Check if matches include pattern
                if self._matches_pattern(file, pattern, case_sensitive):
                    full_path = os.path.join(root, file)
                    matches.append(full_path)

        return matches

    def _matches_pattern(self, filename: str, pattern: str, case_sensitive: bool) -> bool:
        """Check if filename matches pattern."""
        if not case_sensitive:
            filename = filename.lower()
            pattern = pattern.lower()

        return fnmatch.fnmatch(filename, pattern)

    def _matches_any_pattern(self, filename: str, patterns: list[str], case_sensitive: bool) -> bool:
        """Check if filename matches any of the patterns."""
        return any(self._matches_pattern(filename, p, case_sensitive) for p in patterns)

    def _sort_by_mtime(self, files: list[str]) -> list[str]:
        """Sort files by modification time (most recent first)."""
        return sorted(
            files,
            key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0,
            reverse=True
        )

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LangChain adapter."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match (e.g., '*.py', '**/*.ts')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: current directory)",
                        "default": None
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns to exclude (e.g., ['node_modules', '.git'])",
                        "default": []
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum recursion depth (null = unlimited)",
                        "default": None
                    },
                    "sort_by_mtime": {
                        "type": "boolean",
                        "description": "Sort by modification time (most recent first)",
                        "default": False
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive matching",
                        "default": True
                    },
                    "head_limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": None
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N results",
                        "default": 0
                    }
                },
                "required": ["pattern"]
            }
        }


# ============================================================================
# GrepTool v2
# ============================================================================

class GrepToolV2(AsyncToolInterface):
    """Enhanced content search tool matching Claude Code standards.

    Features:
    - Context lines (before/after/around)
    - Output modes (content/files/count)
    - Multiline matching
    - Pagination (head_limit + offset)
    - Security validators integration
    """

    name = "grep_v2"
    description = (
        "Search file contents with advanced features: context lines, output modes, "
        "multiline matching, pagination, and security validation."
    )

    def __init__(self, root_dir: str | None = None):
        """Initialize GrepTool v2.

        Args:
            root_dir: Root directory for sandboxing (workspace root)
        """
        self.root_dir = root_dir

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute grep search with full validation and security checks."""
        # Parse and validate input
        try:
            input_data = GrepSearchInput(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "error_code": "INVALID_INPUT"
            }

        pattern = input_data.pattern
        path = _resolve_search_path(self.root_dir, input_data.path)
        glob_pattern = kwargs.get("glob_pattern") or getattr(input_data, "glob_pattern", None) or getattr(input_data, "glob", None)
        show_line_numbers = getattr(input_data, "show_line_numbers", None)
        if show_line_numbers is None:
            show_line_numbers = getattr(input_data, "line_numbers", True)
        output_mode = input_data.output_mode

        # Security validation: path traversal
        traversal_decision = validate_path_traversal_filesystem(path, self.root_dir)
        if traversal_decision.behavior in [PermissionBehavior.DENY, PermissionBehavior.ASK]:
            return {
                "success": False,
                "error": traversal_decision.message,
                "error_code": "PATH_TRAVERSAL"
            }

        # Master filesystem validator
        fs_decision = validate_filesystem_operation(
            file_path=path,
            operation="read",
            workspace_root=self.root_dir
        )

        if fs_decision.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": fs_decision.message,
                "error_code": "PERMISSION_DENIED"
            }

        try:
            # Compile regex pattern
            flags = 0
            if not input_data.case_sensitive:
                flags |= re.IGNORECASE
            if input_data.multiline:
                flags |= re.MULTILINE | re.DOTALL

            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {
                    "success": False,
                    "error": f"Invalid regex pattern: {e}",
                    "error_code": "INVALID_PATTERN"
                }

            # Search files
            if os.path.isfile(path):
                files_to_search = [path]
            else:
                files_to_search = self._find_files(path, glob_pattern)

            # Perform search based on output mode
            if output_mode in {"files", "files_with_matches"}:
                results = self._search_files_mode(files_to_search, regex)
            elif output_mode == "count":
                results = self._search_count_mode(files_to_search, regex)
            else:  # CONTENT mode
                results = self._search_content_mode(
                    files_to_search,
                    regex,
                    context_before=input_data.context_before,
                    context_after=input_data.context_after,
                    show_line_numbers=show_line_numbers
                )

            # Apply pagination
            total_results = len(results)

            if input_data.offset > 0:
                results = results[input_data.offset:]

            if input_data.head_limit is not None:
                results = results[:input_data.head_limit]

            return {
                "success": True,
                "results": results,
                "total_results": total_results,
                "returned_results": len(results),
                "pattern": pattern,
                "path": path,
                "output_mode": output_mode,
                "offset": input_data.offset,
                "truncated": input_data.head_limit is not None and len(results) < (total_results - input_data.offset)
            }

        except Exception as e:
            _logger.error(f"Error in grep search: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Grep search failed: {e}",
                "error_code": "GREP_ERROR"
            }

    def _find_files(self, path: str, glob_pattern: str | None) -> list[str]:
        """Find all files to search."""
        files = []

        for root, _, filenames in os.walk(path):
            for filename in filenames:
                # Skip if glob pattern provided and doesn't match
                if glob_pattern and not fnmatch.fnmatch(filename, glob_pattern):
                    continue

                full_path = os.path.join(root, filename)
                files.append(full_path)

        return files

    def _search_files_mode(self, files: list[str], regex: re.Pattern) -> list[dict[str, Any]]:
        """Search mode: return only file paths with matches."""
        results = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if regex.search(content):
                    results.append({
                        "file": file_path
                    })

            except Exception as e:
                _logger.debug(f"Error reading {file_path}: {e}")
                continue

        return results

    def _search_count_mode(self, files: list[str], regex: re.Pattern) -> list[dict[str, Any]]:
        """Search mode: return match counts per file."""
        results = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                matches = regex.findall(content)
                if matches:
                    results.append({
                        "file": file_path,
                        "count": len(matches)
                    })

            except Exception as e:
                _logger.debug(f"Error reading {file_path}: {e}")
                continue

        return results

    def _search_content_mode(
        self,
        files: list[str],
        regex: re.Pattern,
        context_before: int,
        context_after: int,
        show_line_numbers: bool
    ) -> list[dict[str, Any]]:
        """Search mode: return matching lines with context."""
        results = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if regex.flags & re.DOTALL:
                    match = regex.search(content)
                    if match:
                        lines = content.splitlines()
                        start_line = content[:match.start()].count("\n") + 1
                        results.append(
                            {
                                "file": file_path,
                                "line_number": start_line,
                                "line": match.group(),
                                "context": match.group(),
                            }
                        )
                        continue

                lines = content.splitlines(keepends=True)

                # Find matching lines
                for line_num, line in enumerate(lines):
                    if regex.search(line):
                        # Calculate context range
                        start = max(0, line_num - context_before)
                        end = min(len(lines), line_num + context_after + 1)

                        # Extract context lines
                        context_lines = []
                        for i in range(start, end):
                            prefix = f"{i + 1}:" if show_line_numbers else ""
                            marker = ">" if i == line_num else " "
                            context_lines.append(f"{marker}{prefix}{lines[i].rstrip()}")

                        results.append({
                            "file": file_path,
                            "line_number": line_num + 1,
                            "line": line.rstrip(),
                            "context": "\n".join(context_lines)
                        })

            except Exception as e:
                _logger.debug(f"Error reading {file_path}: {e}")
                continue

        return results

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LangChain adapter."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory to search in",
                        "default": None
                    },
                    "glob_pattern": {
                        "type": "string",
                        "description": "Filter files by glob pattern (e.g., '*.py')",
                        "default": None
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_with_matches", "count"],
                        "description": "Output mode: content (lines), files (paths), count (counts)",
                        "default": "content"
                    },
                    "context_before": {
                        "type": "integer",
                        "description": "Lines of context before match",
                        "default": 0
                    },
                    "context_after": {
                        "type": "integer",
                        "description": "Lines of context after match",
                        "default": 0
                    },
                    "show_line_numbers": {
                        "type": "boolean",
                        "description": "Show line numbers in output",
                        "default": True
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive matching",
                        "default": True
                    },
                    "multiline": {
                        "type": "boolean",
                        "description": "Enable multiline matching",
                        "default": False
                    },
                    "head_limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": None
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N results",
                        "default": 0
                    }
                },
                "required": ["pattern"]
            }
        }
