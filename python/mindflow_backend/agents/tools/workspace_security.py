"""Shared security helpers for sandboxed agent tools.

Provides Docker sandbox availability checking with graceful fallback
to subprocess sandbox when Docker is not available.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

_logger = get_logger(__name__)

# Cache for Docker availability check
_docker_available_cache: bool | None = None
_docker_checked: bool = False


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


def check_docker_available(*, force_recheck: bool = False) -> bool:
    """Check if Docker is available and running on the system.

    Uses cached result unless force_recheck is True.
    Checks:
    1. docker binary exists in PATH
    2. docker daemon is responding (docker info)

    Args:
        force_recheck: If True, ignore cache and recheck.

    Returns:
        True if Docker is available and running, False otherwise.
    """
    global _docker_available_cache, _docker_checked

    if _docker_checked and not force_recheck:
        return _docker_available_cache or False

    _docker_checked = True

    # Check if docker binary exists
    if not shutil.which("docker"):
        _logger.info(
            "docker_not_found_in_path",
            message="Docker binary not found in PATH. Falling back to subprocess sandbox.",
        )
        _docker_available_cache = False
        return False

    # Check if docker daemon is running
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            _logger.info("docker_available", message="Docker is available and running.")
            _docker_available_cache = True
            return True
        else:
            _logger.warning(
                "docker_daemon_not_running",
                message="Docker daemon is not responding. Falling back to subprocess sandbox.",
                stderr=result.stderr[:200] if result.stderr else "",
            )
            _docker_available_cache = False
            return False
    except subprocess.TimeoutExpired:
        _logger.warning(
            "docker_check_timeout",
            message="Docker check timed out. Falling back to subprocess sandbox.",
        )
        _docker_available_cache = False
        return False
    except Exception as exc:
        _logger.warning(
            "docker_check_error",
            message="Error checking Docker availability. Falling back to subprocess sandbox.",
            error=str(exc),
        )
        _docker_available_cache = False
        return False


def get_sandbox_type() -> str:
    """Determine which sandbox type to use based on Docker availability.

    Returns:
        "docker" if Docker is available, "subprocess" otherwise.
    """
    settings = get_settings()
    force_subprocess = settings.get_feature_flag("sandbox_force_subprocess", False)

    if force_subprocess:
        _logger.info("sandbox_force_subprocess", message="Forced subprocess sandbox via feature flag.")
        return "subprocess"

    if check_docker_available():
        return "docker"

    _logger.info(
        "sandbox_fallback_subprocess",
        message="Docker unavailable. Using subprocess sandbox with security validators.",
    )
    return "subprocess"


def get_docker_sandbox_config() -> dict[str, Any]:
    """Get Docker sandbox configuration from settings.

    Returns:
        Dictionary with Docker sandbox configuration.
    """
    settings = get_settings()
    return {
        "image": settings.get_feature_flag("sandbox_docker_image", "mindflow-sandbox:latest"),
        "memory_limit": settings.get_feature_flag("sandbox_memory_limit", "512m"),
        "cpu_limit": settings.get_feature_flag("sandbox_cpu_limit", "1.0"),
        "network_mode": settings.get_feature_flag("sandbox_network_mode", "none"),
        "timeout_seconds": settings.get_feature_flag("sandbox_timeout_seconds", 120),
        "read_only_root_fs": settings.get_feature_flag("sandbox_read_only_root_fs", True),
        "tmpfs_size": settings.get_feature_flag("sandbox_tmpfs_size", "64m"),
    }


def reset_docker_cache() -> None:
    """Reset the Docker availability cache.

    Useful for testing or when Docker status may have changed.
    """
    global _docker_available_cache, _docker_checked
    _docker_available_cache = None
    _docker_checked = False
    _logger.debug("docker_cache_reset")
