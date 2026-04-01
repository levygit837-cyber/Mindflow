"""Git integration for MindFlow tools.

Provides git operations tracking, diff generation, and history management
for file operations tools.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ============================================================================
# Git Diff Generation
# ============================================================================

async def fetch_single_file_git_diff(
    file_path: str,
    root_dir: str | None = None
) -> dict[str, Any]:
    """Fetch git diff for a single file.

    Args:
        file_path: Path to the file
        root_dir: Root directory (workspace root)

    Returns:
        Dict with diff information:
        - success: bool
        - diff: str (unified diff format)
        - has_changes: bool
        - error: str (if failed)
    """
    try:
        # Resolve absolute path
        abs_path = Path(file_path).resolve()
        if not abs_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "has_changes": False
            }

        # Determine working directory
        cwd = root_dir or str(abs_path.parent)

        # Check if file is in a git repository
        check_cmd = ["git", "rev-parse", "--git-dir"]
        check_result = await asyncio.create_subprocess_exec(
            *check_cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await check_result.communicate()

        if check_result.returncode != 0:
            return {
                "success": False,
                "error": "Not a git repository",
                "has_changes": False
            }

        # Get diff for the file
        diff_cmd = ["git", "diff", "HEAD", "--", str(abs_path)]
        diff_result = await asyncio.create_subprocess_exec(
            *diff_cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await diff_result.communicate()

        if diff_result.returncode != 0:
            return {
                "success": False,
                "error": f"Git diff failed: {stderr.decode('utf-8', errors='replace')}",
                "has_changes": False
            }

        diff_output = stdout.decode('utf-8', errors='replace')

        return {
            "success": True,
            "diff": diff_output,
            "has_changes": len(diff_output.strip()) > 0,
            "file_path": str(abs_path)
        }

    except Exception as e:
        _logger.error(f"Error fetching git diff: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Exception: {e}",
            "has_changes": False
        }


def fetch_single_file_git_diff_sync(
    file_path: str,
    root_dir: str | None = None
) -> dict[str, Any]:
    """Synchronous version of fetch_single_file_git_diff.

    Args:
        file_path: Path to the file
        root_dir: Root directory (workspace root)

    Returns:
        Dict with diff information
    """
    try:
        # Resolve absolute path
        abs_path = Path(file_path).resolve()
        if not abs_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "has_changes": False
            }

        # Determine working directory
        cwd = root_dir or str(abs_path.parent)

        # Check if file is in a git repository
        check_result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True
        )

        if check_result.returncode != 0:
            return {
                "success": False,
                "error": "Not a git repository",
                "has_changes": False
            }

        # Get diff for the file
        diff_result = subprocess.run(
            ["git", "diff", "HEAD", "--", str(abs_path)],
            cwd=cwd,
            capture_output=True,
            text=True
        )

        if diff_result.returncode != 0:
            return {
                "success": False,
                "error": f"Git diff failed: {diff_result.stderr}",
                "has_changes": False
            }

        diff_output = diff_result.stdout

        return {
            "success": True,
            "diff": diff_output,
            "has_changes": len(diff_output.strip()) > 0,
            "file_path": str(abs_path)
        }

    except Exception as e:
        _logger.error(f"Error fetching git diff: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Exception: {e}",
            "has_changes": False
        }


# ============================================================================
# Git Status Tracking
# ============================================================================

async def get_git_status(root_dir: str) -> dict[str, Any]:
    """Get git status for a directory.

    Args:
        root_dir: Root directory to check

    Returns:
        Dict with status information:
        - success: bool
        - branch: str
        - modified: list[str]
        - untracked: list[str]
        - staged: list[str]
        - error: str (if failed)
    """
    try:
        cwd = Path(root_dir).resolve()

        # Check if git repository
        check_cmd = ["git", "rev-parse", "--git-dir"]
        check_result = await asyncio.create_subprocess_exec(
            *check_cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await check_result.communicate()

        if check_result.returncode != 0:
            return {
                "success": False,
                "error": "Not a git repository"
            }

        # Get current branch
        branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        branch_result = await asyncio.create_subprocess_exec(
            *branch_cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        branch_stdout, _ = await branch_result.communicate()
        branch = branch_stdout.decode('utf-8', errors='replace').strip()

        # Get status
        status_cmd = ["git", "status", "--porcelain"]
        status_result = await asyncio.create_subprocess_exec(
            *status_cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        status_stdout, _ = await status_result.communicate()
        status_output = status_stdout.decode('utf-8', errors='replace')

        # Parse status
        modified = []
        untracked = []
        staged = []

        for line in status_output.splitlines():
            if not line.strip():
                continue

            status_code = line[:2]
            file_path = line[3:].strip()

            if status_code[0] in ('M', 'A', 'D', 'R', 'C'):
                staged.append(file_path)
            if status_code[1] == 'M':
                modified.append(file_path)
            if status_code == '??':
                untracked.append(file_path)

        return {
            "success": True,
            "branch": branch,
            "modified": modified,
            "untracked": untracked,
            "staged": staged,
            "is_clean": len(modified) == 0 and len(untracked) == 0 and len(staged) == 0
        }

    except Exception as e:
        _logger.error(f"Error getting git status: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Exception: {e}"
        }


# ============================================================================
# Git Blame Integration
# ============================================================================

async def get_git_blame(
    file_path: str,
    line_number: int | None = None,
    root_dir: str | None = None
) -> dict[str, Any]:
    """Get git blame information for a file or specific line.

    Args:
        file_path: Path to the file
        line_number: Optional line number to blame
        root_dir: Root directory (workspace root)

    Returns:
        Dict with blame information:
        - success: bool
        - blame: str (full blame output) or dict (single line)
        - error: str (if failed)
    """
    try:
        abs_path = Path(file_path).resolve()
        if not abs_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        cwd = root_dir or str(abs_path.parent)

        # Build blame command
        blame_cmd = ["git", "blame"]
        if line_number is not None:
            blame_cmd.extend(["-L", f"{line_number},{line_number}"])
        blame_cmd.append(str(abs_path))

        # Execute blame
        blame_result = await asyncio.create_subprocess_exec(
            *blame_cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await blame_result.communicate()

        if blame_result.returncode != 0:
            return {
                "success": False,
                "error": f"Git blame failed: {stderr.decode('utf-8', errors='replace')}"
            }

        blame_output = stdout.decode('utf-8', errors='replace')

        # Parse single line blame
        if line_number is not None and blame_output.strip():
            parts = blame_output.split(maxsplit=3)
            if len(parts) >= 4:
                return {
                    "success": True,
                    "blame": {
                        "commit": parts[0],
                        "author": parts[1].strip('()'),
                        "date": parts[2],
                        "line": parts[3] if len(parts) > 3 else ""
                    }
                }

        return {
            "success": True,
            "blame": blame_output,
            "file_path": str(abs_path)
        }

    except Exception as e:
        _logger.error(f"Error getting git blame: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Exception: {e}"
        }


# ============================================================================
# Git Operations Tracking
# ============================================================================

class GitOperationTracker:
    """Track git operations performed by tools."""

    def __init__(self):
        """Initialize tracker."""
        self._operations: list[dict[str, Any]] = []

    def track_operation(
        self,
        operation_type: str,
        file_path: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """Track a git operation.

        Args:
            operation_type: Type of operation (read, write, edit, etc.)
            file_path: Path to the file
            details: Additional operation details
        """
        operation = {
            "type": operation_type,
            "file_path": file_path,
            "timestamp": None,  # Would use datetime.now() in production
            "details": details or {}
        }
        self._operations.append(operation)
        _logger.debug(f"Tracked git operation: {operation_type} on {file_path}")

    def get_operations(self) -> list[dict[str, Any]]:
        """Get all tracked operations.

        Returns:
            List of operation dicts
        """
        return self._operations.copy()

    def clear_operations(self) -> None:
        """Clear all tracked operations."""
        self._operations.clear()

    def get_operations_for_file(self, file_path: str) -> list[dict[str, Any]]:
        """Get operations for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of operation dicts for the file
        """
        return [
            op for op in self._operations
            if op["file_path"] == file_path
        ]


# Global tracker instance
_git_tracker = GitOperationTracker()


def track_git_operation(
    operation_type: str,
    file_path: str,
    details: dict[str, Any] | None = None
) -> None:
    """Track a git operation (convenience function).

    Args:
        operation_type: Type of operation
        file_path: Path to the file
        details: Additional details
    """
    _git_tracker.track_operation(operation_type, file_path, details)


def get_git_operations() -> list[dict[str, Any]]:
    """Get all tracked git operations.

    Returns:
        List of operation dicts
    """
    return _git_tracker.get_operations()


def clear_git_operations() -> None:
    """Clear all tracked git operations."""
    _git_tracker.clear_operations()


# ============================================================================
# Diff Visualization
# ============================================================================

def format_diff_for_display(diff: str, max_lines: int = 50) -> str:
    """Format git diff for display.

    Args:
        diff: Raw git diff output
        max_lines: Maximum lines to include

    Returns:
        Formatted diff string
    """
    if not diff or not diff.strip():
        return "(no changes)"

    lines = diff.splitlines()

    if len(lines) <= max_lines:
        return diff

    # Truncate and add indicator
    truncated = "\n".join(lines[:max_lines])
    remaining = len(lines) - max_lines
    truncated += f"\n\n... ({remaining} more lines)"

    return truncated


def parse_diff_stats(diff: str) -> dict[str, Any]:
    """Parse diff statistics.

    Args:
        diff: Raw git diff output

    Returns:
        Dict with statistics:
        - additions: int
        - deletions: int
        - files_changed: int
    """
    additions = 0
    deletions = 0
    files_changed = 0

    for line in diff.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1
        elif line.startswith('diff --git'):
            files_changed += 1

    return {
        "additions": additions,
        "deletions": deletions,
        "files_changed": files_changed,
        "total_changes": additions + deletions
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "fetch_single_file_git_diff",
    "fetch_single_file_git_diff_sync",
    "get_git_status",
    "get_git_blame",
    "track_git_operation",
    "get_git_operations",
    "clear_git_operations",
    "format_diff_for_display",
    "parse_diff_stats",
    "GitOperationTracker",
]
