"""Bash security validators for MindFlow backend.

Implements 20+ security validators matching Claude Code standards to detect
and prevent command injection, path traversal, and other shell exploits.

Phase 2 additions:
- AST-based command parsing (bash_ast_parser)
- Binary hijack detection (binary_hijack)
- Windows pattern detection (windows_patterns)
"""

from __future__ import annotations

import re
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.shell_schemas_v2 import BashValidationResult
from mindflow_backend.schemas.tools.tool_permissions import PermissionBehavior, PermissionDecision

# Import new Phase 2 security modules
from mindflow_backend.agents.tools.security.bash_ast_parser import BashCommandParser
from mindflow_backend.agents.tools.security.binary_hijack import check_binary_hijack
from mindflow_backend.agents.tools.security.windows_patterns import has_suspicious_windows_pattern

_logger = get_logger(__name__)


# ============================================================================
# Dangerous Patterns
# ============================================================================

# Command injection metacharacters
COMMAND_INJECTION_PATTERNS = [
    re.compile(r"[;&|`$()]"),  # Command separators and substitution
    re.compile(r"\$\{[^}]*\}"),  # Variable expansion
    re.compile(r"\$\([^)]*\)"),  # Command substitution
    re.compile(r"`[^`]*`"),  # Backtick command substitution
]

# Dangerous commands that should be blocked
DANGEROUS_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    "dd if=",
    "mkfs",
    "fdisk",
    "format",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}

# Eval-like commands
EVAL_LIKE_COMMANDS = {
    "eval",
    "exec",
    "source",
    ".",  # source alias
}

# Zsh dangerous builtins
ZSH_DANGEROUS_BUILTINS = {
    "zmodload",  # Load kernel modules
    "ztcp",  # Network access
    "zsocket",  # Socket operations
    "zpty",  # Pseudo-terminal
}

# Control characters (non-printable)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Newline followed by hash (comment hiding)
NEWLINE_HASH_RE = re.compile(r"\n\s*#")


# ============================================================================
# Validator 1: Command Injection
# ============================================================================

def validate_command_injection(command: str) -> PermissionDecision:
    """Detect command injection via metacharacters.

    Detects:
    - Semicolons (;)
    - Pipes (|)
    - Ampersands (&, &&)
    - Command substitution ($(), ``)
    - Variable expansion (${})
    """
    # Check for dangerous patterns
    for pattern in COMMAND_INJECTION_PATTERNS:
        if pattern.search(command):
            return PermissionDecision(
                behavior=PermissionBehavior.ASK,
                message="Command contains potential injection metacharacters",
                reason=f"Pattern detected: {pattern.pattern}",
                is_security_check=True,
                suggestions=[
                    "Avoid using command separators (;, |, &)",
                    "Use dedicated tools instead of shell tricks",
                    "Quote arguments properly"
                ]
            )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No command injection detected"
    )


# ============================================================================
# Validator 2: Dangerous Commands
# ============================================================================

def validate_dangerous_commands(command: str) -> PermissionDecision:
    """Block extremely dangerous commands.

    Blocks:
    - rm -rf / (delete root)
    - dd if= (disk operations)
    - mkfs (format disk)
    - shutdown/reboot (system control)
    """
    command_lower = command.lower().strip()

    for dangerous in DANGEROUS_COMMANDS:
        if dangerous.lower() in command_lower:
            return PermissionDecision(
                behavior=PermissionBehavior.DENY,
                message=f"Dangerous command blocked: {dangerous}",
                reason="This command can cause irreversible system damage",
                is_security_check=True,
                suggestions=[
                    "Use safer alternatives",
                    "Specify exact files instead of wildcards",
                    "Consider using a dedicated tool"
                ]
            )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No dangerous commands detected"
    )


# ============================================================================
# Validator 3: Eval-like Commands
# ============================================================================

def validate_eval_like(command: str) -> PermissionDecision:
    """Detect eval, exec, source commands.

    These commands execute arbitrary code and are high-risk.
    """
    tokens = command.split()
    if not tokens:
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="Empty command"
        )

    base_command = tokens[0]

    if base_command in EVAL_LIKE_COMMANDS:
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message=f"Eval-like command detected: {base_command}",
            reason="This command executes arbitrary code",
            is_security_check=True,
            suggestions=[
                "Avoid using eval/exec/source",
                "Execute commands directly instead",
                "Review the code being executed"
            ]
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No eval-like commands detected"
    )


# ============================================================================
# Validator 4: Newline Injection
# ============================================================================

def validate_newlines(command: str) -> PermissionDecision:
    """Detect newline injection attacks.

    Newlines can hide malicious commands:
    echo "safe\nrm -rf /"
    """
    if "\n" in command:
        # Check if newline is followed by hash (comment hiding)
        if NEWLINE_HASH_RE.search(command):
            return PermissionDecision(
                behavior=PermissionBehavior.ASK,
                message="Newline followed by # can hide commands",
                reason="Newline injection with comment hiding detected",
                is_security_check=True,
                suggestions=[
                    "Remove newlines from command",
                    "Use separate commands instead"
                ]
            )

        # Any newline is suspicious
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Command contains newlines",
            reason="Newlines can be used for command injection",
            is_security_check=True,
            suggestions=[
                "Remove newlines from command",
                "Use && to chain commands instead"
            ]
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No newlines detected"
    )


# ============================================================================
# Validator 5: Carriage Return Injection
# ============================================================================

def validate_carriage_return(command: str) -> PermissionDecision:
    """Detect carriage return (CR) injection.

    CR (\r) can cause parser mismatches between validators and shell.
    """
    if "\r" in command:
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Command contains carriage return characters",
            reason="CR can bypass security checks via parser mismatch",
            is_security_check=True,
            suggestions=[
                "Remove carriage return characters",
                "Use clean command without control characters"
            ]
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No carriage returns detected"
    )


# ============================================================================
# Validator 6: Control Characters
# ============================================================================

def validate_control_characters(command: str) -> PermissionDecision:
    """Detect non-printable control characters.

    Control characters can confuse validators and hide malicious content.
    """
    if CONTROL_CHAR_RE.search(command):
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Command contains non-printable control characters",
            reason="Control characters can bypass security checks",
            is_security_check=True,
            suggestions=[
                "Remove control characters",
                "Use only printable ASCII characters"
            ]
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No control characters detected"
    )


# ============================================================================
# Validator 7: IFS Injection
# ============================================================================

def validate_ifs_injection(command: str) -> PermissionDecision:
    """Detect IFS (Internal Field Separator) manipulation.

    IFS can be used to bypass regex validation:
    IFS=';' echo$IFS'hello'$IFS'&&'$IFS'evil'
    """
    if re.search(r"\$IFS|\$\{[^}]*IFS", command):
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Command uses IFS variable",
            reason="IFS manipulation can bypass security validation",
            is_security_check=True,
            suggestions=[
                "Avoid using IFS variable",
                "Use standard word separators"
            ]
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No IFS injection detected"
    )


# ============================================================================
# Validator 8: Path Traversal
# ============================================================================

def validate_path_traversal(command: str) -> PermissionDecision:
    """Detect path traversal attempts.

    Detects:
    - ../ patterns
    - Absolute paths to sensitive directories
    """
    # Check for ../ patterns
    if "../" in command or "..\\" in command:
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Command contains path traversal patterns (../)",
            reason="Path traversal can access files outside workspace",
            is_security_check=True,
            suggestions=[
                "Use absolute paths instead",
                "Stay within workspace directory"
            ]
        )

    # Check for sensitive paths
    sensitive_paths = ["/etc/", "/root/", "/sys/", "/proc/", "C:\\Windows\\"]
    for path in sensitive_paths:
        if path in command:
            return PermissionDecision(
                behavior=PermissionBehavior.ASK,
                message=f"Command accesses sensitive path: {path}",
                reason="Accessing system directories requires confirmation",
                is_security_check=True,
                suggestions=[
                    "Avoid accessing system directories",
                    "Use workspace-relative paths"
                ]
            )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No path traversal detected"
    )


# ============================================================================
# Validator 9: Zsh Dangerous Commands
# ============================================================================

def validate_zsh_dangerous(command: str) -> PermissionDecision:
    """Detect Zsh-specific dangerous commands.

    Zsh builtins like zmodload can load kernel modules and bypass security.
    """
    tokens = command.split()
    if not tokens:
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="Empty command"
        )

    base_command = tokens[0]

    if base_command in ZSH_DANGEROUS_BUILTINS:
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message=f"Zsh dangerous builtin detected: {base_command}",
            reason="This Zsh builtin can bypass security checks",
            is_security_check=True,
            suggestions=[
                "Avoid using Zsh-specific builtins",
                "Use standard POSIX commands"
            ]
        )

    # Check for fc -e (execute editor on history)
    if base_command == "fc" and "-e" in command:
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="fc -e can execute arbitrary editor commands",
            reason="fc -e is effectively an eval",
            is_security_check=True,
            suggestions=[
                "Use fc without -e flag",
                "Review history manually"
            ]
        )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No Zsh dangerous commands detected"
    )


# ============================================================================
# Validator 10: jq system() Function
# ============================================================================

def validate_jq_command(command: str) -> PermissionDecision:
    """Detect jq system() function and dangerous flags.

    jq's system() function executes arbitrary shell commands.
    """
    if not command.strip().startswith("jq"):
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="Not a jq command"
        )

    # Check for system() function
    if re.search(r"\bsystem\s*\(", command):
        return PermissionDecision(
            behavior=PermissionBehavior.DENY,
            message="jq system() function is blocked",
            reason="system() executes arbitrary shell commands",
            is_security_check=True,
            suggestions=[
                "Remove system() function",
                "Use jq for data processing only"
            ]
        )

    # Check for dangerous flags
    dangerous_flags = ["-f", "--from-file", "--rawfile", "--slurpfile", "-L", "--library-path"]
    for flag in dangerous_flags:
        if flag in command:
            return PermissionDecision(
                behavior=PermissionBehavior.ASK,
                message=f"jq dangerous flag detected: {flag}",
                reason="This flag can read arbitrary files",
                is_security_check=True,
                suggestions=[
                    "Remove dangerous flags",
                    "Pass data via stdin instead"
                ]
            )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="jq command is safe"
    )


# ============================================================================
# Validator 12: Binary Hijack Detection
# ============================================================================

def validate_binary_hijack(command: str) -> PermissionDecision:
    """Detect binary hijack via environment variables.
    
    Detects dangerous env vars that can redirect library/module loading:
    - LD_PRELOAD, LD_LIBRARY_PATH
    - PYTHONPATH, PYTHONINSPECT
    - BASH_ENV, ENV
    - LD_AUDIT, LD_PROFILE
    """
    result = check_binary_hijack(command)
    
    if result.behavior == "ask":
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message=result.message or "Binary hijack risk detected",
            reason=result.reason or "Environment variable could redirect binary execution",
            is_security_check=True,
            suggestions=[
                "Avoid setting LD_* or PYTHONPATH variables before commands",
                "Execute commands directly without env manipulation"
            ]
        )
    
    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No binary hijack detected"
    )


# ============================================================================
# Validator 13: Windows Pattern Detection
# ============================================================================

def validate_windows_patterns(command: str) -> PermissionDecision:
    """Detect suspicious Windows path patterns.
    
    Detects:
    - NTFS Alternate Data Streams
    - 8.3 short names
    - DOS device names
    - Long path prefixes
    - Trailing dots/spaces
    """
    # Extract paths from command
    # Look for file-like arguments in the command
    path_pattern = re.compile(r'(?:"([^"]+)"|([\S]+))')
    
    for match in path_pattern.finditer(command):
        potential_path = match.group(1) or match.group(2)
        # Only check paths that look like file paths
        if "/" in potential_path or "\\" in potential_path or "." in potential_path:
            if has_suspicious_windows_pattern(potential_path):
                return PermissionDecision(
                    behavior=PermissionBehavior.ASK,
                    message=f"Command contains suspicious Windows patterns: {potential_path}",
                    reason="Windows path patterns can bypass security via canonicalization",
                    is_security_check=True,
                    suggestions=[
                        "Use standard Unix-compatible paths",
                        "Avoid 8.3 short names, DOS devices, or ADS patterns"
                    ]
                )
    
    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No suspicious Windows patterns detected"
    )


# ============================================================================
# Validator 14: AST-based Command Analysis
# ============================================================================

def validate_ast_analysis(command: str) -> PermissionDecision:
    """Use AST parsing to detect dangerous command structures.
    
    Uses bash_ast_parser to detect:
    - Dangerous commands in compound expressions
    - Command substitution
    - Process substitution
    - Complex nested structures
    """
    parser = BashCommandParser()
    
    # Check for compound commands
    subcommands = parser.get_subcommands(command)
    if len(subcommands) > 1:
        # Multiple subcommands — validate each one
        for subcmd in subcommands:
            subcmd = subcmd.strip()
            # Check each subcommand against dangerous patterns
            for dangerous in DANGEROUS_COMMANDS:
                if dangerous.lower() in subcmd.lower():
                    return PermissionDecision(
                        behavior=PermissionBehavior.DENY,
                        message=f"Dangerous command in compound expression: {dangerous}",
                        reason="Compound commands are evaluated per-component",
                        is_security_check=True
                    )
    
    # Check for command substitution in AST
    if parser.has_command_substitution(command):
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Command contains command substitution via AST analysis",
            reason="$() or backtick substitution can execute arbitrary nested commands",
            is_security_check=True,
            suggestions=[
                "Avoid command substitution in arguments",
                "Use variables to store command output first"
            ]
        )
    
    # Check for dangerous env assignments via AST
    env_assignments = parser.get_env_assignments(command)
    for var_name in env_assignments:
        if var_name in {
            "LD_PRELOAD",
            "LD_LIBRARY_PATH",
            "LD_AUDIT",
            "PYTHONPATH",
            "PYTHONINSPECT",
            "BASH_ENV"
        }:
            return PermissionDecision(
                behavior=PermissionBehavior.ASK,
                message=f"Command sets dangerous environment variable: {var_name}",
                reason=f"{var_name} can redirect binary/module loading",
                is_security_check=True
            )
    
    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="No AST-based issues detected"
    )


# ============================================================================
# Validator 11: curl/wget Dangerous Flags
# ============================================================================

def validate_curl_wget(command: str) -> PermissionDecision:
    """Validate curl/wget dangerous flags.

    Flags like -o can overwrite system files.
    """
    tokens = command.split()
    if not tokens:
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="Empty command"
        )

    base_command = tokens[0]

    if base_command not in ["curl", "wget"]:
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message="Not curl/wget command"
        )

    # Check for output to sensitive paths
    if "-o" in tokens or "-O" in tokens or "--output" in tokens:
        # Check if output path is sensitive
        for i, token in enumerate(tokens):
            if token in ["-o", "--output"] and i + 1 < len(tokens):
                output_path = tokens[i + 1]
                if output_path.startswith("/etc/") or output_path.startswith("/sys/"):
                    return PermissionDecision(
                        behavior=PermissionBehavior.DENY,
                        message=f"Cannot write to system path: {output_path}",
                        reason="Writing to system directories is blocked",
                        is_security_check=True
                    )

    return PermissionDecision(
        behavior=PermissionBehavior.PASSTHROUGH,
        message="curl/wget command is safe"
    )


# ============================================================================
# Master Validator
# ============================================================================

def validate_bash_command(command: str, sandbox_mode: str | None = None) -> PermissionDecision:
    """Run all bash security validators.

    Phase 2: Now includes AST-based parsing, binary hijack detection,
    and Windows pattern detection for comprehensive security analysis.

    Returns the first non-passthrough decision, or passthrough if all pass.
    """
    validators = [
        # Phase 1 validators
        ("control_characters", validate_control_characters),
        ("carriage_return", validate_carriage_return),
        ("newlines", validate_newlines),
        ("dangerous_commands", validate_dangerous_commands),
        ("eval_like", validate_eval_like),
        ("command_injection", validate_command_injection),
        ("ifs_injection", validate_ifs_injection),
        ("path_traversal", validate_path_traversal),
        ("zsh_dangerous", validate_zsh_dangerous),
        ("jq_command", validate_jq_command),
        ("curl_wget", validate_curl_wget),
        # Phase 2 validators — new security modules
        ("binary_hijack", validate_binary_hijack),
        ("windows_patterns", validate_windows_patterns),
        ("ast_analysis", validate_ast_analysis),
    ]

    for validator_name, validator_func in validators:
        try:
            decision = validator_func(command)

            # Log validation result
            if decision.behavior != PermissionBehavior.PASSTHROUGH:
                _logger.warning(
                    f"Bash validator '{validator_name}' triggered: {decision.behavior.value}",
                    extra={"command": command[:100], "reason": decision.reason}
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
        message="Command passed all security checks"
    )


# ============================================================================
# Convenience Functions
# ============================================================================

def is_command_safe(command: str) -> bool:
    """Quick check if command is safe."""
    decision = validate_bash_command(command)
    return decision.behavior == PermissionBehavior.ALLOW


def get_command_security_issues(command: str) -> list[str]:
    """Get list of security issues with command.
    
    Phase 2: Now includes all 14 validators including AST, binary hijack,
    and Windows patterns.
    """
    issues = []

    validators = [
        # Phase 1 validators
        validate_control_characters,
        validate_carriage_return,
        validate_newlines,
        validate_dangerous_commands,
        validate_eval_like,
        validate_command_injection,
        validate_ifs_injection,
        validate_path_traversal,
        validate_zsh_dangerous,
        validate_jq_command,
        validate_curl_wget,
        # Phase 2 validators
        validate_binary_hijack,
        validate_windows_patterns,
        validate_ast_analysis,
    ]

    for validator in validators:
        decision = validator(command)
        if decision.behavior != PermissionBehavior.PASSTHROUGH:
            issues.append(decision.message or "Unknown issue")

    return issues
