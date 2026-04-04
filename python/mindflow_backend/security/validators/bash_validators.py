"""Security-package compatibility adapter for bash validation.

This module preserves the legacy ``security`` contract while delegating
actual validation logic to the canonical validator in
``agents.tools.security.bash_validators``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mindflow_backend.agents.tools.security.bash_validators import (
    validate_bash_command as _canonical_validate_bash_command,
)
from mindflow_backend.schemas.tools.tool_permissions import PermissionBehavior

_LEGACY_STRICT_EVAL_RE = re.compile(r"^\s*(?:eval|exec|source|\.)\b")
_LEGACY_STRICT_SHELL_EXEC_RE = re.compile(r"^\s*(?:bash|sh)\s+-c\b")
_LEGACY_BINARY_HIJACK_RE = re.compile(
    r"^\s*(?:"
    r"LD_PRELOAD|LD_LIBRARY_PATH|LD_AUDIT|LD_PROFILE|"
    r"DYLD_INSERT_LIBRARIES|PYTHONPATH|PYTHONINSPECT|BASH_ENV|ENV"
    r")="
)


@dataclass
class SecurityDecision:
    """Compatibility decision model exposed by ``mindflow_backend.security``."""

    behavior: str
    message: str
    severity: str


def _uses_legacy_strict_eval(command: str) -> bool:
    """Return True when legacy security rules require a hard block."""
    return bool(
        _LEGACY_STRICT_EVAL_RE.search(command)
        or _LEGACY_STRICT_SHELL_EXEC_RE.search(command)
    )


def _uses_legacy_binary_hijack(command: str) -> bool:
    """Return True when legacy rules require blocking env-based hijacks."""
    return bool(_LEGACY_BINARY_HIJACK_RE.search(command))


def _from_canonical_behavior(behavior: PermissionBehavior | str) -> str:
    """Map canonical permission behavior to the security compatibility surface."""
    normalized = (
        behavior.value
        if isinstance(behavior, PermissionBehavior)
        else str(behavior).lower()
    )
    if normalized in {
        PermissionBehavior.ALLOW.value,
        PermissionBehavior.PASSTHROUGH.value,
    }:
        return "passthrough"
    if normalized == PermissionBehavior.DENY.value:
        return "block"
    return "ask"


def validate_bash_command(
    command: str,
    sandbox_mode: str | None = None,
) -> SecurityDecision:
    """Validate a bash command using the canonical validator.

    The canonical validator owns the actual security logic. This adapter keeps
    the older ``security`` package response contract and preserves the legacy
    hard-block behavior for eval-like execution and binary hijack environment
    variables.
    """
    canonical = _canonical_validate_bash_command(command, sandbox_mode)
    behavior = _from_canonical_behavior(canonical.behavior)
    message = canonical.message or "Command validated successfully"

    if behavior == "passthrough":
        return SecurityDecision(
            behavior="passthrough",
            message=message,
            severity="low",
        )

    if behavior == "block":
        return SecurityDecision(
            behavior="block",
            message=message,
            severity="critical",
        )

    if _uses_legacy_strict_eval(command):
        return SecurityDecision(
            behavior="block",
            message=message,
            severity="high",
        )

    if _uses_legacy_binary_hijack(command):
        return SecurityDecision(
            behavior="block",
            message=message,
            severity="critical",
        )

    return SecurityDecision(
        behavior="ask",
        message=message,
        severity="medium",
    )


__all__ = ["SecurityDecision", "validate_bash_command"]
