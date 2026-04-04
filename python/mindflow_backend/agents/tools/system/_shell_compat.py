"""Shared compatibility helpers for shell adapters.

These helpers keep legacy shell response contracts consistent across
temporary compatibility surfaces while the canonical shell implementation
remains unsuffixed.
"""

from __future__ import annotations

import os
from typing import Any

LEGACY_SHELL_DANGEROUS_PATTERNS: tuple[str, ...] = (
    "rm -rf /",
    "mkfs",
    "dd if=",
    "> /dev/",
    ":(){ :|:& };:",
    "chmod -R 777",
    "chown -R",
)

LEGACY_SHELL_ERROR_MAP: dict[str, str] = {
    "workspace security error": "PERMISSION_DENIED",
    "command blocked by secure sandbox policy": "DANGEROUS_COMMAND",
    "write command blocked in read-only sandbox mode": "READ_ONLY_MODE",
}


def get_legacy_dangerous_command_error(command: str) -> dict[str, Any] | None:
    """Return the legacy wrapper error for obviously destructive shell commands."""
    command_lower = command.lower()
    for pattern in LEGACY_SHELL_DANGEROUS_PATTERNS:
        if pattern.lower() in command_lower:
            return {
                "success": False,
                "error": f"Dangerous command pattern detected: {pattern}",
                "error_code": "DANGEROUS_COMMAND",
                "command": command[:100],
            }
    return None


def resolve_explicit_shell_working_dir(
    working_dir: str | None,
    *,
    root_dir: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Resolve and validate an explicitly provided working directory."""
    if not working_dir:
        return None, None

    resolved = working_dir
    if root_dir and not os.path.isabs(resolved):
        resolved = os.path.join(root_dir, resolved)
    resolved = os.path.abspath(resolved)

    if not os.path.exists(resolved):
        return None, {
            "success": False,
            "error": f"Working directory not found: {resolved}",
            "error_code": "DIRECTORY_NOT_FOUND",
            "working_dir": resolved,
        }

    return resolved, None


def normalize_shell_output_text(value: Any) -> str:
    """Normalize output markers used by compatibility wrappers."""
    if not isinstance(value, str):
        return ""
    if value.endswith("\n...[truncated]"):
        return value.replace("\n...[truncated]", "\n...[output truncated]")
    return value


def normalize_legacy_shell_result(
    payload: dict[str, Any],
    *,
    command: str,
    check_return_code: bool,
) -> dict[str, Any]:
    """Normalize shell payloads to the compatibility contract shared by wrappers."""
    normalized = dict(payload)
    normalized["timed_out"] = normalized.pop("timeout", False)
    normalized.setdefault("command", command[:200])
    normalized["output"] = normalize_shell_output_text(normalized.get("output", ""))
    normalized["stderr"] = normalize_shell_output_text(normalized.get("stderr", ""))

    combined_output = f"{normalized['output']}\n{normalized['stderr']}".lower()
    if normalized.get("return_code") == 127 and "not found" in combined_output:
        return {
            "success": False,
            "error": normalized["stderr"] or normalized["output"] or "Command not found",
            "error_code": "COMMAND_NOT_FOUND",
            "command": command[:100],
        }

    if check_return_code and normalized.get("return_code", 0) != 0:
        normalized["success"] = False
        normalized["error"] = (
            normalized["stderr"]
            or normalized["output"]
            or "Command failed"
        )
        normalized["error_code"] = "EXECUTION_ERROR"

    return normalized


__all__ = [
    "LEGACY_SHELL_ERROR_MAP",
    "get_legacy_dangerous_command_error",
    "normalize_legacy_shell_result",
    "resolve_explicit_shell_working_dir",
]
