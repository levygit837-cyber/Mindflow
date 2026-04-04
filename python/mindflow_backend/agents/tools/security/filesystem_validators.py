"""Filesystem security validators for MindFlow backend.

Implements security validators for filesystem operations including:
- Device file blocking
- Symlink validation
- TOCTOU protection
- Path traversal detection
- Secret detection
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.tool_permissions import (
    PermissionBehavior,
    PermissionDecision,
)

_logger = get_logger(__name__)


# ============================================================================
# Blocked Device Paths
# ============================================================================

BLOCKED_DEVICE_PATHS = {
    # Infinite output devices
    "/dev/zero",
    "/dev/random",
    "/dev/urandom",
    "/dev/full",
    # Blocking input devices
    "/dev/stdin",
    "/dev/tty",
    "/dev/console",
    # Output devices (nonsensical to read)
    "/dev/stdout",
    "/dev/stderr",
    # File descriptor aliases
    "/dev/fd/0",
    "/dev/fd/1",
    "/dev/fd/2",
}


# ============================================================================
# Secret Patterns
# ============================================================================

SECRET_PATTERNS = [
    # API Keys
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?"),
    re.compile(r"(?i)(secret[_-]?key|secretkey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?"),

    # AWS
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key ID
    re.compile(r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?"),

    # GitHub
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub Personal Access Token
    re.compile(r"gho_[a-zA-Z0-9]{36}"),  # GitHub OAuth Token
    re.compile(r"github[_-]?token\s*[:=]\s*['\"]?([a-zA-Z0-9]{40})['\"]?", re.IGNORECASE),

    # OpenAI
    re.compile(r"sk-[a-zA-Z0-9]{48}"),  # OpenAI API Key
    re.compile(r"sk-proj-[a-zA-Z0-9]{48}"),  # OpenAI Project API Key

    # Google
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # Google API Key

    # Slack
    re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}"),

    # Generic tokens
    re.compile(r"(?i)(token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{32,})['\"]?"),

    # Passwords
    re.compile(r"(?i)password\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?"),

    # Private keys
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


# ============================================================================
# Validator 1: Device File Blocking
# ============================================================================

def validate_device_file(file_path: str) -> PermissionDecision:
    """Block reading from device files that can hang or produce infinite output.

    Blocks:
    - /dev/zero (infinite zeros)
    - /dev/random (infinite random data)
    - /dev/stdin (blocks waiting for input)
    - /dev/tty (blocks waiting for input)
    """
    # Normalize path
    normalized = os.path.normpath(file_path)

    # Check blocked device paths
    if normalized in BLOCKED_DEVICE_PATHS:
        return PermissionDecision(
            behavior=PermissionBehavior.DENY,
            message=f"Cannot read from device file: {normalized}",
            reason="This device file can hang the process or produce infinite output",
            is_security_check=True,
            suggestions=[
                "Use regular files instead of device files",
                "If you need random data, use a library function"
            ]
        )

    # Check /proc/*/fd/* patterns (Linux fd aliases)
    if "/proc/" in normalized and "/fd/" in normalized:
        if normalized.endswith("/fd/0") or normalized.endswith("/fd/1") or normalized.endswith("/fd/2"):
            return PermissionDecision(
                behavior=PermissionBehavior.DENY,
                message=f"Cannot read from file descriptor: {normalized}",
                reason="Reading from stdin/stdout/stderr can hang the process",
                is_security_check=True
            )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="Not a blocked device file"
    )


# ============================================================================
# Validator 2: Symlink Validation
# ============================================================================

def validate_symlink(file_path: str, workspace_root: str | None = None) -> PermissionDecision:
    """Validate symbolic links don't point outside workspace.

    Prevents symlink attacks where a symlink points to sensitive files.
    """
    path = Path(file_path)

    # Check if path is a symlink
    if not path.is_symlink():
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="Not a symlink"
        )

    try:
        # Resolve symlink to real path
        real_path = path.resolve(strict=True)

        # If workspace_root is provided, check if real path is within workspace
        if workspace_root:
            workspace = Path(workspace_root).resolve()

            # Check if real_path is within workspace
            try:
                real_path.relative_to(workspace)
            except ValueError:
                return PermissionDecision(
                    behavior=PermissionBehavior.DENY,
                    message=f"Symlink points outside workspace: {file_path} -> {real_path}",
                    reason="Symlinks must point to files within workspace",
                    is_security_check=True,
                    suggestions=[
                        "Use direct file paths instead of symlinks",
                        "Ensure symlink target is within workspace"
                    ]
                )

        # Check if symlink points to sensitive system paths
        sensitive_paths = ["/etc", "/root", "/sys", "/proc"]
        real_path_str = str(real_path)

        for sensitive in sensitive_paths:
            if real_path_str.startswith(sensitive):
                return PermissionDecision(
                    behavior=PermissionBehavior.ASK,
                    message=f"Symlink points to sensitive path: {real_path}",
                    reason="Accessing system directories requires confirmation",
                    is_security_check=True
                )

    except (OSError, RuntimeError) as e:
        return PermissionDecision(
            behavior=PermissionBehavior.DENY,
            message=f"Cannot resolve symlink: {file_path}",
            reason=f"Symlink resolution failed: {e}",
            is_security_check=True
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="Symlink is safe"
    )


# ============================================================================
# Validator 3: TOCTOU Protection
# ============================================================================

class TOCTOUValidator:
    """Time-of-Check-Time-of-Use protection for file operations.

    Prevents race conditions where file is modified between check and use.
    """

    def __init__(self):
        self._file_mtimes: dict[str, float] = {}

    def record_mtime(self, file_path: str) -> float | None:
        """Record modification time of file before operation."""
        try:
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            self._file_mtimes[file_path] = mtime
            return mtime
        except OSError:
            return None

    def validate_mtime(self, file_path: str) -> PermissionDecision:
        """Validate file hasn't been modified since record_mtime."""
        if file_path not in self._file_mtimes:
            return PermissionDecision(
                behavior=PermissionBehavior.PASSTHROUGH,
                message="No previous mtime recorded"
            )

        try:
            stat = os.stat(file_path)
            current_mtime = stat.st_mtime
            recorded_mtime = self._file_mtimes[file_path]

            if current_mtime != recorded_mtime:
                return PermissionDecision(
                    behavior=PermissionBehavior.DENY,
                    message="File was modified during operation",
                    reason="TOCTOU race condition detected",
                    is_security_check=True,
                    suggestions=[
                        "Retry the operation",
                        "Ensure no other process is modifying the file"
                    ]
                )
        except OSError as e:
            return PermissionDecision(
                behavior=PermissionBehavior.DENY,
                message=f"Cannot check file modification time: {e}",
                reason="File may have been deleted or moved",
                is_security_check=True
            )

        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="File has not been modified"
        )

    def clear(self, file_path: str | None = None):
        """Clear recorded mtimes."""
        if file_path:
            self._file_mtimes.pop(file_path, None)
        else:
            self._file_mtimes.clear()


# Global TOCTOU validator instance
_toctou_validator = TOCTOUValidator()


def record_file_mtime(file_path: str) -> float | None:
    """Record file modification time before operation."""
    return _toctou_validator.record_mtime(file_path)


def validate_file_mtime(file_path: str) -> PermissionDecision:
    """Validate file hasn't been modified since record."""
    return _toctou_validator.validate_mtime(file_path)


def clear_file_mtime(file_path: str | None = None):
    """Clear recorded modification times."""
    _toctou_validator.clear(file_path)


# ============================================================================
# Validator 4: Path Traversal
# ============================================================================

def validate_path_traversal_filesystem(file_path: str, workspace_root: str | None = None) -> PermissionDecision:
    """Validate path doesn't traverse outside workspace.

    Detects:
    - ../ patterns
    - Absolute paths outside workspace
    """
    path = Path(file_path)

    # Check for ../ patterns
    if ".." in path.parts:
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Path contains parent directory references (..)",
            reason="Path traversal can access files outside workspace",
            is_security_check=True,
            suggestions=[
                "Use absolute paths instead",
                "Stay within workspace directory"
            ]
        )

    # If workspace_root provided, validate path is within workspace
    if workspace_root:
        try:
            workspace = Path(workspace_root).resolve()
            resolved_path = path.resolve()

            # Check if path is within workspace
            try:
                resolved_path.relative_to(workspace)
            except ValueError:
                return PermissionDecision(
                    behavior=PermissionBehavior.DENY,
                    message=f"Path is outside workspace: {file_path}",
                    reason="Access is restricted to workspace directory",
                    is_security_check=True,
                    suggestions=[
                        "Use paths within workspace",
                        f"Workspace root: {workspace}"
                    ]
                )
        except (OSError, RuntimeError) as e:
            return PermissionDecision(
                behavior=PermissionBehavior.DENY,
                message=f"Cannot resolve path: {file_path}",
                reason=f"Path resolution failed: {e}",
                is_security_check=True
            )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="Path is safe"
    )


# ============================================================================
# Validator 5: Secret Detection
# ============================================================================

def validate_secrets(content: str, file_path: str | None = None) -> PermissionDecision:
    """Detect secrets in file content.

    Detects:
    - API keys
    - Tokens
    - Passwords
    - Private keys
    """
    detected_secrets = []

    for pattern in SECRET_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            # Get pattern description
            pattern_str = pattern.pattern[:50]
            detected_secrets.append(pattern_str)

    if detected_secrets:
        file_info = f" in {file_path}" if file_path else ""
        return PermissionDecision(
            behavior=PermissionBehavior.DENY,
            message=f"Secrets detected{file_info}",
            reason=f"Found {len(detected_secrets)} potential secret(s)",
            is_security_check=True,
            suggestions=[
                "Remove secrets from code",
                "Use environment variables instead",
                "Use a secret management service",
                "Add secrets to .gitignore"
            ]
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No secrets detected"
    )


# ============================================================================
# Validator 6: File Size Limits
# ============================================================================

def validate_file_size(file_path: str, max_size_bytes: int = 1024 * 1024 * 1024) -> PermissionDecision:
    """Validate file size doesn't exceed limit.

    Default limit: 1 GiB (prevents OOM)
    """
    try:
        stat = os.stat(file_path)
        size = stat.st_size

        if size > max_size_bytes:
            size_mb = size / (1024 * 1024)
            limit_mb = max_size_bytes / (1024 * 1024)

            return PermissionDecision(
                behavior=PermissionBehavior.DENY,
                message=f"File too large: {size_mb:.1f} MB (limit: {limit_mb:.1f} MB)",
                reason="Large files can cause out-of-memory errors",
                is_security_check=False,
                suggestions=[
                    "Use pagination (offset/limit) to read file in chunks",
                    "Process file in streaming mode"
                ]
            )
    except OSError:
        # File doesn't exist or can't stat - let other validators handle
        pass

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="File size is acceptable"
    )


# ============================================================================
# Master Filesystem Validator
# ============================================================================

def validate_filesystem_operation(
    file_path: str,
    operation: str,  # "read", "write", "edit"
    content: str | None = None,
    workspace_root: str | None = None,
    check_secrets: bool = True,
    check_size: bool = True,
) -> PermissionDecision:
    """Run all filesystem security validators.

    Args:
        file_path: Path to file
        operation: Operation type (read/write/edit)
        content: File content (for secret detection)
        workspace_root: Workspace root directory
        check_secrets: Whether to check for secrets
        check_size: Whether to check file size

    Returns:
        First non-passthrough decision, or passthrough if all pass
    """
    validators = [
        ("device_file", lambda: validate_device_file(file_path)),
        ("symlink", lambda: validate_symlink(file_path, workspace_root)),
        ("path_traversal", lambda: validate_path_traversal_filesystem(file_path, workspace_root)),
    ]

    # Add size check for read operations
    if check_size and operation == "read":
        validators.append(("file_size", lambda: validate_file_size(file_path)))

    # Add secret check for write/edit operations
    if check_secrets and content and operation in ["write", "edit"]:
        validators.append(("secrets", lambda: validate_secrets(content, file_path)))

    for validator_name, validator_func in validators:
        try:
            decision = validator_func()

            # Log validation result
            if decision.behavior != PermissionBehavior.PASSTHROUGH:
                _logger.warning(
                    f"Filesystem validator '{validator_name}' triggered: {decision.behavior.value}",
                    extra={"file_path": file_path, "operation": operation, "reason": decision.reason}
                )

            # Return first non-passthrough decision
            if decision.behavior != PermissionBehavior.PASSTHROUGH:
                return decision

        except Exception as e:
            _logger.error(f"Validator '{validator_name}' failed: {e}", exc_info=True)
            # Continue to next validator on error

    # All validators passed
    return PermissionDecision(
        behavior=PermissionBehavior.ALLOW,
        message="Filesystem operation passed all security checks"
    )
