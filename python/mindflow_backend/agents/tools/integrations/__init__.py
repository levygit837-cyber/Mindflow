"""Integration modules for MindFlow tools.

Provides integrations with external systems like git, LSP, and file history.
"""

from __future__ import annotations

from .file_history import (
    FileHistoryStore,
    get_file_history,
    get_history_store,
    rollback_file,
    track_file_edit,
)
from .git_integration import (
    fetch_single_file_git_diff,
    fetch_single_file_git_diff_sync,
    format_diff_for_display,
    get_git_blame,
    get_git_operations,
    get_git_status,
    parse_diff_stats,
    track_git_operation,
)

__all__ = [
    # Git integration
    "fetch_single_file_git_diff",
    "fetch_single_file_git_diff_sync",
    "get_git_status",
    "get_git_blame",
    "track_git_operation",
    "get_git_operations",
    "format_diff_for_display",
    "parse_diff_stats",
    # File history
    "FileHistoryStore",
    "get_history_store",
    "track_file_edit",
    "rollback_file",
    "get_file_history",
]
