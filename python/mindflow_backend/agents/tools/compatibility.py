"""Backward compatibility layer for tools v1 → v2 migration.

Provides deprecation warnings, aliases, and migration helpers to ensure
smooth transition from v1 tools to v2 tools without breaking existing code.
"""

from __future__ import annotations

import warnings
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ============================================================================
# Deprecation Warnings
# ============================================================================

def _emit_deprecation_warning(
    old_tool: str,
    new_tool: str,
    version: str = "v2.0.0",
    removal_version: str = "v3.0.0"
) -> None:
    """Emit a deprecation warning for old tool usage.

    Args:
        old_tool: Name of the deprecated tool
        new_tool: Name of the replacement tool
        version: Version where deprecation started
        removal_version: Version where tool will be removed
    """
    message = (
        f"{old_tool} is deprecated since {version} and will be removed in {removal_version}. "
        f"Please use {new_tool} instead."
    )
    warnings.warn(message, DeprecationWarning, stacklevel=3)
    _logger.warning(f"Deprecation: {message}")


# ============================================================================
# Tool Aliases (v1 → v2)
# ============================================================================

class ToolAlias:
    """Wrapper that forwards calls to v2 tool while emitting deprecation warning."""

    def __init__(self, v2_tool: Any, old_name: str, new_name: str):
        """Initialize tool alias.

        Args:
            v2_tool: The v2 tool instance to forward to
            old_name: Name of the deprecated v1 tool
            new_name: Name of the new v2 tool
        """
        self._v2_tool = v2_tool
        self._old_name = old_name
        self._new_name = new_name
        self._warning_emitted = False

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to v2 tool."""
        # Emit warning only once per instance
        if not self._warning_emitted:
            _emit_deprecation_warning(self._old_name, self._new_name)
            self._warning_emitted = True

        return getattr(self._v2_tool, name)

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Forward execute call to v2 tool."""
        if not self._warning_emitted:
            _emit_deprecation_warning(self._old_name, self._new_name)
            self._warning_emitted = True

        return await self._v2_tool.execute(**kwargs)


def create_v1_alias(v2_tool: Any, old_name: str, new_name: str) -> ToolAlias:
    """Create a v1 tool alias that forwards to v2 tool.

    Args:
        v2_tool: The v2 tool instance
        old_name: Name of the deprecated v1 tool
        new_name: Name of the new v2 tool

    Returns:
        ToolAlias instance that forwards to v2 tool
    """
    return ToolAlias(v2_tool, old_name, new_name)


# ============================================================================
# Parameter Migration Helpers
# ============================================================================

def migrate_read_file_params(v1_params: dict[str, Any]) -> dict[str, Any]:
    """Migrate FileReadTool v1 parameters to v2 format.

    Changes:
    - No breaking changes, v2 is superset of v1
    - New optional params: offset, limit, include_line_numbers, encoding, pages

    Args:
        v1_params: Parameters in v1 format

    Returns:
        Parameters in v2 format
    """
    v2_params = v1_params.copy()

    # v2 defaults (if not specified)
    v2_params.setdefault("include_line_numbers", True)
    v2_params.setdefault("encoding", "utf-8")

    return v2_params


def migrate_write_file_params(v1_params: dict[str, Any]) -> dict[str, Any]:
    """Migrate FileWriteTool v1 parameters to v2 format.

    Changes:
    - No breaking changes, v2 is superset of v1
    - New optional params: atomic, backup, preserve_permissions, check_secrets, generate_git_diff

    Args:
        v1_params: Parameters in v1 format

    Returns:
        Parameters in v2 format
    """
    v2_params = v1_params.copy()

    # v2 defaults (if not specified)
    v2_params.setdefault("atomic", True)
    v2_params.setdefault("backup", False)
    v2_params.setdefault("preserve_permissions", True)
    v2_params.setdefault("check_secrets", True)
    v2_params.setdefault("generate_git_diff", False)

    return v2_params


def migrate_edit_file_params(v1_params: dict[str, Any]) -> dict[str, Any]:
    """Migrate FileEditTool v1 parameters to v2 format.

    Changes:
    - No breaking changes, v2 is superset of v1
    - New optional params: replace_all, fuzzy_match, fuzzy_threshold, preserve_quotes,
      dry_run, check_secrets, generate_git_diff

    Args:
        v1_params: Parameters in v1 format

    Returns:
        Parameters in v2 format
    """
    v2_params = v1_params.copy()

    # v2 defaults (if not specified)
    v2_params.setdefault("replace_all", False)
    v2_params.setdefault("fuzzy_match", False)
    v2_params.setdefault("fuzzy_threshold", 0.8)
    v2_params.setdefault("preserve_quotes", True)
    v2_params.setdefault("dry_run", False)
    v2_params.setdefault("check_secrets", True)
    v2_params.setdefault("generate_git_diff", False)

    return v2_params


def migrate_glob_params(v1_params: dict[str, Any]) -> dict[str, Any]:
    """Migrate GlobSearchTool v1 parameters to v2 format.

    Changes:
    - No breaking changes, v2 is superset of v1
    - New optional params: exclude_patterns, max_depth, sort_by_mtime, case_sensitive,
      head_limit, offset

    Args:
        v1_params: Parameters in v1 format

    Returns:
        Parameters in v2 format
    """
    v2_params = v1_params.copy()

    # v2 defaults (if not specified)
    v2_params.setdefault("exclude_patterns", [])
    v2_params.setdefault("max_depth", None)
    v2_params.setdefault("sort_by_mtime", False)
    v2_params.setdefault("case_sensitive", True)
    v2_params.setdefault("head_limit", None)
    v2_params.setdefault("offset", 0)

    return v2_params


def migrate_grep_params(v1_params: dict[str, Any]) -> dict[str, Any]:
    """Migrate GrepSearchTool v1 parameters to v2 format.

    Changes:
    - No breaking changes, v2 is superset of v1
    - New optional params: glob_pattern, output_mode, context_before, context_after,
      show_line_numbers, case_sensitive, multiline, head_limit, offset

    Args:
        v1_params: Parameters in v1 format

    Returns:
        Parameters in v2 format
    """
    v2_params = v1_params.copy()

    # v2 defaults (if not specified)
    v2_params.setdefault("glob_pattern", None)
    v2_params.setdefault("output_mode", "content")
    v2_params.setdefault("context_before", 0)
    v2_params.setdefault("context_after", 0)
    v2_params.setdefault("show_line_numbers", True)
    v2_params.setdefault("case_sensitive", True)
    v2_params.setdefault("multiline", False)
    v2_params.setdefault("head_limit", None)
    v2_params.setdefault("offset", 0)

    return v2_params


def migrate_shell_params(v1_params: dict[str, Any]) -> dict[str, Any]:
    """Migrate ShellExecutorTool v1 parameters to v2 format.

    Changes:
    - No breaking changes, v2 is superset of v1
    - New optional params: run_in_background, sandbox_mode

    Args:
        v1_params: Parameters in v1 format

    Returns:
        Parameters in v2 format
    """
    v2_params = v1_params.copy()

    # v2 defaults (if not specified)
    v2_params.setdefault("run_in_background", False)
    v2_params.setdefault("sandbox_mode", None)

    return v2_params


# ============================================================================
# Migration Guide
# ============================================================================

MIGRATION_GUIDE = """
# Tools v1 → v2 Migration Guide

## Overview

MindFlow tools have been upgraded to v2 to match Claude Code standards.
All v1 tools are deprecated and will be removed in v3.0.0.

## Breaking Changes

**None** - v2 is a superset of v1. All v1 parameters are supported in v2.

## New Features in v2

### FileReadToolV2
- `offset`, `limit` - Pagination for large files
- `include_line_numbers` - Add line numbers to output
- `encoding` - Specify file encoding
- `pages` - Read specific PDF pages
- Device file blocking (/dev/zero, /dev/random)
- Symlink validation
- Image support (base64 encoding)

### FileWriteToolV2
- `atomic` - Atomic write (temp + rename)
- `backup` - Create backup before overwrite
- `preserve_permissions` - Preserve file permissions
- `check_secrets` - Detect and block secrets
- `generate_git_diff` - Generate git diff
- Metadata tracking

### FileEditToolV2
- `replace_all` - Replace all occurrences
- `fuzzy_match` - Fuzzy string matching
- `preserve_quotes` - Preserve quote style
- `dry_run` - Preview changes without applying
- `check_secrets` - Detect and block secrets
- `generate_git_diff` - Generate git diff
- TOCTOU protection

### GlobToolV2
- `exclude_patterns` - Exclude files/dirs
- `max_depth` - Limit recursion depth
- `sort_by_mtime` - Sort by modification time
- `case_sensitive` - Case-sensitive matching
- `head_limit`, `offset` - Pagination

### GrepToolV2
- `glob_pattern` - Filter by file pattern
- `output_mode` - content/files/count
- `context_before`, `context_after` - Context lines
- `show_line_numbers` - Show line numbers
- `case_sensitive` - Case-sensitive search
- `multiline` - Multiline matching
- `head_limit`, `offset` - Pagination

### ShellExecutorToolV2
- `run_in_background` - Background execution
- `sandbox_mode` - Sandbox mode override
- All 11 bash security validators
- Command semantic analysis
- Security level classification

## Migration Steps

1. **Update imports:**
   ```python
   # Old (v1)
   from mindflow_backend.agents.tools.filesystem import FileReadTool

   # New (v2)
   from mindflow_backend.agents.tools.filesystem.file_operations_v2 import FileReadToolV2
   ```

2. **Update tool instantiation:**
   ```python
   # Old (v1)
   tool = FileReadTool()

   # New (v2)
   tool = FileReadToolV2()
   ```

3. **No parameter changes needed** - v1 parameters work in v2

4. **Optional: Use new v2 features**
   ```python
   # Example: Use pagination
   result = await tool.execute(
       file_path="/path/to/large.txt",
       offset=100,
       limit=50
   )
   ```

## Deprecation Timeline

- **v2.0.0** (2026-04-01): v2 tools released, v1 deprecated
- **v2.5.0** (2026-07-01): Deprecation warnings added
- **v3.0.0** (2026-10-01): v1 tools removed

## Support

For questions or issues, see:
- Documentation: `docs/tools/API-REFERENCE.md`
- Examples: `docs/tools/MIGRATION-GUIDE.md`
"""


def print_migration_guide() -> None:
    """Print the migration guide to console."""
    print(MIGRATION_GUIDE)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "create_v1_alias",
    "migrate_read_file_params",
    "migrate_write_file_params",
    "migrate_edit_file_params",
    "migrate_glob_params",
    "migrate_grep_params",
    "migrate_shell_params",
    "print_migration_guide",
    "MIGRATION_GUIDE",
]
