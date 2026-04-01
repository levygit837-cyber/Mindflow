"""Binary Hijack Detection — Detect environment variable-based binary hijacking.

Detects attempts to hijack binary execution via dangerous environment variables
like LD_PRELOAD, LD_LIBRARY_PATH, PYTHONPATH, etc.

Adapted from Claude Code's BINARY_HIJACK_VARS in bashPermissions.ts.

These variables can redirect shared library loading or Python module imports,
allowing an attacker to execute arbitrary code when a target binary runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from mindflow_backend.schemas.tools.tool_permissions import PermissionResult


# ---------------------------------------------------------------------------
# Dangerous environment variables
# ---------------------------------------------------------------------------


class HijackVarCategory(StrEnum):
    """Categories of hijack vectors."""

    LD_LOADER = "ld_loader"  # LD_PRELOAD, LD_LIBRARY_PATH
    LD_DEBUG = "ld_debug"  # LD_DEBUG, LD_AUDIT
    PYTHON = "python"  # PYTHONPATH, PYTHONINSPECT
    SHELL = "shell"  # BASH_ENV, ENV, PROMPT_COMMAND
    PATH = "path"  # PATH manipulation


# Complete set of dangerous environment variables, organized by category
HIJACK_VARS_BY_CATEGORY: dict[HijackVarCategory, set[str]] = {
    HijackVarCategory.LD_LOADER: {
        "LD_PRELOAD",  # Preload shared libraries
        "LD_LIBRARY_PATH",  # Library search path
        "LD_ORIGIN_PATH",  # Origin for $ORIGIN
    },
    HijackVarCategory.LD_DEBUG: {
        "LD_DEBUG",  # Dynamic linker debug
        "LD_DEBUG_OUTPUT",  # Debug output file
        "LD_AUDIT",  # Library auditing
        "LD_AUDIT_VERBOSE",  # Verbose auditing
        "LD_PROFILE",  # Function profiling
        "LD_PROFILE_OUTPUT",  # Profile output
        "LD_STATIC_TLS_EXTRA",  # Extra TLS space
    },
    HijackVarCategory.PYTHON: {
        "PYTHONPATH",  # Module search path
        "PYTHONINSPECT",  # Enter interactive mode on exit
        "PYTHONSTARTUP",  # Startup script
        "PYTHONHOME",  # Standard library location
        "PYTHONUSERBASE",  # User base directory
        "PYTHONDONTWRITEBYTECODE",  # Can be used to hide artifacts
        "PYTHONSAFEPATH",  # (Actually a defense, but can be unset)
    },
    HijackVarCategory.SHELL: {
        "BASH_ENV",  # Bash startup file
        "ENV",  # POSIX shell startup file
        "PROMPT_COMMAND",  # Command before prompt
        "BASH_EXEC",  # Bash execution path
        "TMPPREFIX",  # Temp file prefix (bash)
        "GLOBIGNORE",  # Glob ignore pattern
    },
    HijackVarCategory.PATH: {
        "PATH",  # Command search path
        "CDPATH",  # cd search path
        "IFS",  # Internal field separator
        "MAIL",  # Mail file (can trigger on logout)
        "MAILPATH",  # Mail path list
    },
}

# Flattened set for quick lookup
ALL_HIJACK_VARS: set[str] = set()
for _vars in HIJACK_VARS_BY_CATEGORY.values():
    ALL_HIJACK_VARS.update(_vars)


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Pattern: VAR=value command — assignment before command
# Matches: "LD_PRELOAD=/tmp/evil.so ./target"
# Matches: "PYTHONPATH=/tmp/hack python3 script.py"
ENV_ASSIGNMENT_PREFIX = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)"  # Variable name
    r"\s*="  # Equals sign
    r"\s*"  # Optional whitespace
    r"(\S)"  # Non-space char (start of command)
)

# Pattern: export VAR=value; command
# Matches: "export LD_PRELOAD=/tmp/evil.so; ./target"
EXPORT_ASSIGNMENT = re.compile(
    r"^\s*export\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)"  # Variable name
    r"\s*="
)

# Pattern: env VAR=value command
# Matches: "env LD_PRELOAD=/tmp/evil.so ./target"
ENV_COMMAND = re.compile(
    r"^\s*env\s+"
    r"(?:-[a-zA-Z]\s+)*"  # Optional env flags
    r"([A-Za-z_][A-Za-z0-9_]*)"  # Variable name
    r"\s*="
)

# Pattern: VAR=value in subshell
# Matches: "(LD_PRELOAD=/tmp/evil.so ./target)"
# Matches: "{ LD_PRELOAD=/tmp/evil.so ./target; }"
SUBSHELL_ASSIGNMENT = re.compile(
    r"[({]\s*([A-Za-z_][A-Za-z0-9_]*)"
    r"\s*="
)


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------


@dataclass
class HijackDetection:
    """Result of binary hijack detection."""

    is_detected: bool = False
    variable: str | None = None
    category: HijackVarCategory | None = None
    command: str | None = None
    risk_level: str = "low"  # "low", "medium", "high"


def check_binary_hijack(command: str) -> PermissionResult:
    """Check if command sets dangerous environment variables.
    
    Detects patterns like:
    - "LD_PRELOAD=/tmp/evil.so ./target"
    - "export LD_LIBRARY_PATH=/tmp; ./target"
    - "env PYTHONPATH=/tmp/hack python3 script.py"
    
    Args:
        command: The bash command to check.
        
    Returns:
        PermissionResult with behavior='ask' if hijack detected.
    """
    detection = _detect_hijack(command)

    if detection.is_detected and detection.variable in ALL_HIJACK_VARS:
        return PermissionResult(
            behavior="ask",
            message=(
                f"Command sets environment variable '{detection.variable}' which "
                f"could hijack binary execution ({detection.category.value}). "
                f"This requires manual approval."
            ),
            reason_type="binary_hijack",
            variable=detection.variable,
            category=detection.category,
        )

    return PermissionResult(behavior="passthrough")


def _detect_hijack(command: str) -> HijackDetection:
    """Detect environment variable hijack attempts in command.
    
    Checks multiple patterns:
    1. PREFIX=value command
    2. export PREFIX=value; command
    3. env PREFIX=value command
    4. (PREFIX=value command) subshell
    
    Returns:
        HijackDetection with findings.
    """
    result = HijackDetection()

    # Check each pattern type

    # 1. Direct assignment prefix: VAR=value cmd
    match = ENV_ASSIGNMENT_PREFIX.match(command)
    if match:
        var_name = match.group(1)
        if var_name in ALL_HIJACK_VARS:
            result.is_detected = True
            result.variable = var_name
            result.category = _get_category_for_var(var_name)
            result.command = command
            return result

    # 2. Export statement: export VAR=value; cmd
    for match in EXPORT_ASSIGNMENT.finditer(command):
        var_name = match.group(1)
        if var_name in ALL_HIJACK_VARS:
            result.is_detected = True
            result.variable = var_name
            result.category = _get_category_for_var(var_name)
            result.command = command
            return result

    # 3. env command: env VAR=value cmd
    match = ENV_COMMAND.match(command)
    if match:
        var_name = match.group(1)
        if var_name in ALL_HIJACK_VARS:
            result.is_detected = True
            result.variable = var_name
            result.category = _get_category_for_var(var_name)
            result.command = command
            return result

    # 4. Subshell: (VAR=value cmd)
    for match in SUBSHELL_ASSIGNMENT.finditer(command):
        var_name = match.group(1)
        if var_name in ALL_HIJACK_VARS:
            result.is_detected = True
            result.variable = var_name
            result.category = _get_category_for_var(var_name)
            result.command = command
            return result

    return result


def _get_category_for_var(var_name: str) -> HijackVarCategory:
    """Get the hijack category for a given environment variable name."""
    for category, vars_set in HIJACK_VARS_BY_CATEGORY.items():
        if var_name in vars_set:
            return category
    # Fallback: try to categorize heuristically
    if var_name.startswith("LD_"):
        return HijackVarCategory.LD_LOADER
    if var_name.startswith("PYTHON"):
        return HijackVarCategory.PYTHON
    return HijackVarCategory.SHELL


def get_jailbreak_env_values(command: str) -> dict[str, str]:
    """Extract dangerous environment variable assignments from command.
    
    Returns dict of {var_name: var_value} for any dangerous variables found.
    Useful for logging/auditing which values were being set.
    
    Example:
        "LD_PRELOAD=/tmp/evil.so PYTHONDONTWRITEBYTECODE=1 ./target"
        -> {"LD_PRELOAD": "/tmp/evil.so", "PYTHONDONTWRITEBYTECODE": "1"}
    """
    found: dict[str, str] = {}

    # Match VAR=value patterns at start or after ; and &
    assignment_pattern = re.compile(
        r"(?:^|[;&|])\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)"  # Variable name
        r"\s*=\s*"
        r"([^;\s&|]+)"  # Value (until separator)
    )

    for match in assignment_pattern.finditer(command):
        var_name = match.group(1)
        var_value = match.group(2)
        if var_name in ALL_HIJACK_VARS:
            found[var_name] = var_value

    # Also check export statements
    export_pattern = re.compile(
        r"export\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)"
        r"\s*=\s*"
        r"([^;\s&|]+)"
    )
    for match in export_pattern.finditer(command):
        var_name = match.group(1)
        var_value = match.group(2)
        if var_name in ALL_HIJACK_VARS:
            found[var_name] = var_value

    return found


def strip_hijack_env_vars(command: str) -> str:
    """Remove dangerous environment variable assignments from command.
    
    This is a sanitization function that can be used to create a safer
    version of the command by stripping hijack vectors.
    
    WARNING: This is defense-in-depth only. Do not rely on this as the
    sole security control — use proper sandboxing.
    
    Args:
        command: Original command string.
        
    Returns:
        Command with dangerous env var assignments removed.
    """
    result = command

    # Remove leading VAR=value patterns
    for var in ALL_HIJACK_VARS:
        # Pattern: VAR=value at start of command
        pattern = re.compile(rf"^\s*{re.escape(var)}\s*=\s*\S+\s*")
        while pattern.match(result):
            result = pattern.sub("", result)

        # Pattern: ; VAR=value in middle
        pattern = re.compile(rf";\s*{re.escape(var)}\s*=\s*\S*\s*")
        while pattern.search(result):
            result = pattern.sub(";", result)

        # Pattern: export VAR=value
        pattern = re.compile(rf"\bexport\s+{re.escape(var)}\s*=\s*\S*\s*[;]?")
        while pattern.search(result):
            result = pattern.sub("", result)

    return result.strip()