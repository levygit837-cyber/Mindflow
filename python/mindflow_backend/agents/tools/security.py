"""Shared security helpers for sandboxed agent tools."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping

from mindflow_backend.infra.config import get_settings
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode


class WorkspaceSecurityError(ValueError):
    """Raised when a tool tries to escape its assigned workspace."""


_READ_ONLY_PATTERNS = [
    re.compile(r"\btouch\b", re.IGNORECASE),
    re.compile(r"\bmkdir\b", re.IGNORECASE),
    re.compile(r"\brm\b", re.IGNORECASE),
    re.compile(r"\brmdir\b", re.IGNORECASE),
    re.compile(r"\bmv\b", re.IGNORECASE),
    re.compile(r"\bcp\b", re.IGNORECASE),
    re.compile(r"\binstall\b", re.IGNORECASE),
    re.compile(r"\btee\b", re.IGNORECASE),
    re.compile(r"\bdd\b", re.IGNORECASE),
    re.compile(r"\bchmod\b", re.IGNORECASE),
    re.compile(r"\bchown\b", re.IGNORECASE),
    re.compile(r">\s*", re.IGNORECASE),
]

_DANGEROUS_PATTERNS = [
    # Privilege escalation
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bsu\b", re.IGNORECASE),
    re.compile(r"\bdoas\b", re.IGNORECASE),
    # System control
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breboot\b", re.IGNORECASE),
    re.compile(r"\bhalt\b", re.IGNORECASE),
    re.compile(r"\bpoweroff\b", re.IGNORECASE),
    # Disk/mount operations
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bfdisk\b", re.IGNORECASE),
    re.compile(r"\bmount\b", re.IGNORECASE),
    re.compile(r"\bumount\b", re.IGNORECASE),
    # Container destruction
    re.compile(r"\bdocker\s+(rm|rmi|run)\b", re.IGNORECASE),
    re.compile(r"\bpodman\s+(rm|rmi|run)\b", re.IGNORECASE),
    # Destructive git
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-f\b", re.IGNORECASE),
    # Network exfiltration tools
    re.compile(r"\bnc\b", re.IGNORECASE),
    re.compile(r"\bncat\b", re.IGNORECASE),
    re.compile(r"\bnetcat\b", re.IGNORECASE),
    re.compile(r"/dev/tcp/", re.IGNORECASE),
    re.compile(r"/dev/udp/", re.IGNORECASE),
    # Dependency injection
    re.compile(r"\bpip\s+install\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+install\b", re.IGNORECASE),
    re.compile(r"\byarn\s+add\b", re.IGNORECASE),
    # Fork bomb patterns
    re.compile(r":\(\)", re.IGNORECASE),
    re.compile(r"while\s+true", re.IGNORECASE),
]

_SAFE_ENV_KEYS = {
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TMPDIR",
    "TMP",
    "TEMP",
    "CI",
    "FORCE_COLOR",
    "NO_COLOR",
    "COLUMNS",
    "LINES",
}


def secure_sandbox_enabled() -> bool:
    """Return whether secure sandbox behavior is enabled."""
    return get_settings().get_feature_flag("sandbox_secure_runtime", True)


def normalize_sandbox_mode(value: SandboxMode | str | None) -> SandboxMode:
    """Normalize arbitrary sandbox mode inputs."""
    if isinstance(value, SandboxMode):
        return value
    if isinstance(value, str):
        try:
            return SandboxMode(value)
        except ValueError:
            upper = value.upper()
            for mode in SandboxMode:
                if mode.name == upper:
                    return mode
    return SandboxMode.FULL


def resolve_workspace_root(root_dir: str | Path | None) -> Path:
    """Resolve the workspace root used to confine tool operations."""
    return Path(root_dir or Path.cwd()).resolve()


def resolve_workspace_path(raw_path: str | Path, root_dir: str | Path | None) -> Path:
    """Resolve a path and ensure it remains inside the configured workspace.

    Security checks performed:
    1. Symlink detection — symlinks that could point outside the workspace
       are rejected to prevent symlink-chasing escape attacks.
    2. Path containment — resolved path must be inside workspace_root.
    """
    workspace_root = resolve_workspace_root(root_dir)
    candidate = Path(raw_path)

    # Reject symlinks that exist at the candidate path before resolution,
    # since resolving them could silently escape the workspace boundary.
    candidate_abs = candidate if candidate.is_absolute() else (workspace_root / candidate)
    if candidate_abs.is_symlink():
        raise WorkspaceSecurityError(
            f"Symlink detected at path: {candidate_abs}. Symlinks are not allowed inside the workspace."
        )

    resolved = candidate.resolve() if candidate.is_absolute() else (workspace_root / candidate).resolve()

    # Check each component in the resolved path for symlinks (defense in depth
    # against deeply nested symlink chains).
    check = workspace_root
    for part in resolved.relative_to(workspace_root.parent).parts[len(workspace_root.parent.parts):]:
        check = check / part
        if check.is_symlink():
            raise WorkspaceSecurityError(
                f"Symlink component detected in path: {check}. Symlinks are not allowed inside the workspace."
            )

    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise WorkspaceSecurityError(
            f"Path escapes configured workspace: {resolved} is outside {workspace_root}"
        ) from exc

    return resolved


def sanitize_environment(
    extra_env: Mapping[str, str] | None = None,
    *,
    cwd: str | Path | None = None,
) -> dict[str, str]:
    """Build a minimal environment for subprocess execution."""
    env: dict[str, str] = {
        key: value
        for key, value in os.environ.items()
        if key in _SAFE_ENV_KEYS
    }
    effective_cwd = str(Path(cwd).resolve()) if cwd is not None else str(Path.cwd())
    env.setdefault("PATH", os.environ.get("PATH", "/usr/bin:/bin"))
    env["PWD"] = effective_cwd
    env["HOME"] = effective_cwd

    if extra_env:
        for key, value in extra_env.items():
            if key in _SAFE_ENV_KEYS:
                env[key] = value

    return env


def validate_shell_command(command: str, sandbox_mode: SandboxMode | str | None) -> str | None:
    """Return an error message when the command violates secure sandbox policy."""
    normalized = (command or "").strip()
    if not normalized:
        return "Command must be a non-empty string"

    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(normalized):
            return "Command blocked by secure sandbox policy"

    if normalize_sandbox_mode(sandbox_mode) == SandboxMode.READ_ONLY:
        for pattern in _READ_ONLY_PATTERNS:
            if pattern.search(normalized):
                return "Write command blocked in read-only sandbox mode"

    return None


def is_read_only_mode(value: SandboxMode | str | None) -> bool:
    """Convenience helper for filesystem tools."""
    return normalize_sandbox_mode(value) == SandboxMode.READ_ONLY
