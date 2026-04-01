"""Bash command security validators.

Enhanced validators for detecting dangerous bash commands and patterns.
Migrated and improved from agents/tools/security/bash_validators.py
"""

import re
from dataclasses import dataclass
from typing import Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class SecurityDecision:
    """Security validation decision."""
    behavior: str  # "passthrough", "block", "ask"
    message: str
    severity: str  # "critical", "high", "medium", "low"


def validate_dangerous_commands(command: str) -> SecurityDecision | None:
    """Validate against dangerous commands."""
    dangerous = [
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
        ":(){ :|:& };:",  # Fork bomb
        "chmod -R 777 /",
        "chown -R",
        "> /dev/sda",
        "mv /* /dev/null",
    ]

    for pattern in dangerous:
        if pattern in command:
            return SecurityDecision(
                behavior="block",
                message=f"Dangerous command detected: {pattern}",
                severity="critical"
            )
    return None


def validate_command_injection(command: str) -> SecurityDecision | None:
    """Validate against command injection patterns."""
    injection_patterns = [
        r";\s*rm\s",
        r"\|\s*rm\s",
        r"&&\s*rm\s",
        r"`.*rm.*`",
        r"\$\(.*rm.*\)",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, command):
            return SecurityDecision(
                behavior="block",
                message=f"Command injection pattern detected: {pattern}",
                severity="critical"
            )
    return None


def validate_eval_like(command: str) -> SecurityDecision | None:
    """Validate against eval-like commands."""
    eval_commands = ["eval", "exec", "source", ".", "bash -c", "sh -c"]

    for cmd in eval_commands:
        if cmd in command:
            return SecurityDecision(
                behavior="block",
                message=f"Eval-like command detected: {cmd}",
                severity="high"
            )
    return None


def validate_binary_hijack(command: str) -> SecurityDecision | None:
    """Validate against binary hijacking attempts."""
    hijack_patterns = [
        "LD_PRELOAD=",
        "LD_LIBRARY_PATH=",
        "DYLD_INSERT_LIBRARIES=",
    ]

    for pattern in hijack_patterns:
        if pattern in command:
            return SecurityDecision(
                behavior="block",
                message=f"Binary hijack attempt detected: {pattern}",
                severity="critical"
            )
    return None


def validate_path_manipulation(command: str) -> SecurityDecision | None:
    """Validate against PATH manipulation."""
    if re.search(r"PATH=.*(/tmp|/var/tmp)", command):
        return SecurityDecision(
            behavior="block",
            message="PATH manipulation to temporary directory detected",
            severity="high"
        )
    return None


def validate_network_commands(command: str) -> SecurityDecision | None:
    """Validate network commands (will be checked by NetworkPolicy)."""
    network_cmds = ["curl", "wget", "nc", "netcat", "telnet", "ssh", "scp", "ftp"]

    tokens = command.split()
    if tokens and tokens[0] in network_cmds:
        # Let NetworkPolicy handle this
        return None
    return None


def validate_file_operations(command: str) -> SecurityDecision | None:
    """Validate dangerous file operations."""
    if re.search(r"rm\s+-rf\s+/", command):
        return SecurityDecision(
            behavior="block",
            message="Recursive delete of root directory",
            severity="critical"
        )
    return None


def validate_privilege_escalation(command: str) -> SecurityDecision | None:
    """Validate privilege escalation attempts."""
    priv_commands = ["sudo", "su", "doas"]

    tokens = command.split()
    if tokens and tokens[0] in priv_commands:
        return SecurityDecision(
            behavior="block",
            message=f"Privilege escalation attempt: {tokens[0]}",
            severity="critical"
        )
    return None


def validate_system_modification(command: str) -> SecurityDecision | None:
    """Validate system modification commands."""
    sys_commands = ["systemctl", "service", "init", "reboot", "shutdown", "halt"]

    tokens = command.split()
    if tokens and tokens[0] in sys_commands:
        return SecurityDecision(
            behavior="block",
            message=f"System modification command: {tokens[0]}",
            severity="high"
        )
    return None


def validate_package_managers(command: str) -> SecurityDecision | None:
    """Validate package manager commands."""
    pkg_managers = ["apt", "apt-get", "yum", "dnf", "pacman", "brew"]

    tokens = command.split()
    if tokens and tokens[0] in pkg_managers:
        return SecurityDecision(
            behavior="ask",
            message=f"Package manager command: {tokens[0]}",
            severity="medium"
        )
    return None


def validate_compound_commands(command: str) -> SecurityDecision | None:
    """Validate compound commands (split and validate each)."""
    # Split by &&, ||, ;, |
    separators = [" && ", " || ", "; ", " | "]

    subcommands = [command]
    for sep in separators:
        new_subcommands = []
        for cmd in subcommands:
            new_subcommands.extend(cmd.split(sep))
        subcommands = new_subcommands

    # Validate each subcommand
    for subcmd in subcommands:
        subcmd = subcmd.strip()
        if subcmd:
            result = validate_bash_command(subcmd)
            if result.behavior != "passthrough":
                return result

    return None


# List of all validators
VALIDATORS: list[Callable[[str], SecurityDecision | None]] = [
    validate_dangerous_commands,
    validate_command_injection,
    validate_eval_like,
    validate_binary_hijack,
    validate_path_manipulation,
    validate_file_operations,
    validate_privilege_escalation,
    validate_system_modification,
    validate_package_managers,
    validate_network_commands,
]


def validate_bash_command(command: str) -> SecurityDecision:
    """Validate bash command against all security rules.

    Args:
        command: Bash command to validate

    Returns:
        SecurityDecision with behavior (passthrough/block/ask) and message
    """
    # Run all validators
    for validator in VALIDATORS:
        result = validator(command)
        if result is not None:
            _logger.warning(
                "security_validation_failed",
                command=command[:100],
                validator=validator.__name__,
                behavior=result.behavior,
                severity=result.severity,
            )
            return result

    # All validators passed
    return SecurityDecision(
        behavior="passthrough",
        message="Command validated successfully",
        severity="low"
    )
