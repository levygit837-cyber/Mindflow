"""Default permission policies — mirrors Claude Code's built-in safety checks.

Adapted from Claude Code's:
- src/utils/permissions/filesystem.ts (DANGEROUS_FILES, DANGEROUS_DIRECTORIES)
- src/utils/permissions/permissionSetup.ts (dangerous permission detection)
- src/utils/permissions/dangerousPatterns.ts (cross-platform code exec patterns)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mindflow_backend.permissions.types import (
    PermissionBehavior,
    PermissionRule,
    PermissionRuleValue,
    RuleSource,
)

# ---------------------------------------------------------------------------
# Dangerous files — never auto-edit or auto-read without approval
# (From Claude Code's filesystem.ts: DANGEROUS_FILES)
# ---------------------------------------------------------------------------

DANGEROUS_FILES: frozenset[str] = frozenset({
    ".gitconfig",
    ".gitmodules",
    ".bashrc",
    ".bash_profile",
    ".zshrc",
    ".zprofile",
    ".profile",
    ".ripgreprc",
    ".mcp.json",
    ".claude.json",
    ".claude.json.backup",
    "id_rsa",
    "id_ed25519",
    ".env",
    ".env.local",
    ".env.production",
    "secrets.json",
    "credentials.json",
    ".netrc",
    "known_hosts",
})

# ---------------------------------------------------------------------------
# Dangerous directories — never auto-access without approval
# (From Claude Code's filesystem.ts: DANGEROUS_DIRECTORIES)
# ---------------------------------------------------------------------------

DANGEROUS_DIRECTORIES: frozenset[str] = frozenset({
    ".git",
    ".vscode",
    ".idea",
    ".claude",
    ".ssh",
    ".gnupg",
    ".aws",
    ".gcloud",
    ".kube",
    ".docker",
    "node_modules/.cache",
    "__pycache__",
})

# ---------------------------------------------------------------------------
# Dangerous bash patterns — would bypass auto-mode classifier
# (From Claude Code's dangerousPatterns.ts: DANGEROUS_BASH_PATTERNS)
# ---------------------------------------------------------------------------

DANGEROUS_BASH_PATTERNS: frozenset[str] = frozenset({
    "python",
    "python3",
    "python2",
    "node",
    "deno",
    "tsx",
    "ruby",
    "perl",
    "php",
    "lua",
    "npx",
    "bunx",
    "npm run",
    "yarn run",
    "pnpm run",
    "bun run",
    "bash",
    "sh",
    "zsh",
    "fish",
    "eval",
    "exec",
    "env",
    "xargs",
    "sudo",
    "ssh",
    "curl",
    "wget",
    "git",  # git config core.sshCommand / hooks = arbitrary code
    "fa run",  # Anthropic internal
    "coo",  # Cluster code launcher
    "gh",  # GitHub CLI (arbitrary HTTP)
    "gh api",
})

# ---------------------------------------------------------------------------
# Safe tools — don't need permission prompts in any mode
# (From Claude Code's classifierDecision.ts: SAFE_YOLO_ALLOWLISTED_TOOLS)
# ---------------------------------------------------------------------------

SAFE_TOOLS: frozenset[str] = frozenset({
    # Read-only operations
    "FileReadTool",
    "GlobTool",
    "GrepTool",
    "LSPTool",
    "ToolSearchTool",
    "ListMCPResourcesTool",
    "ReadMCPResourceTool",
    # Task management (metadata only)
    "TodoWriteTool",
    "TaskCreateTool",
    "TaskGetTool",
    "TaskUpdateTool",
    "TaskListTool",
    "TaskStopTool",
    "TaskOutputTool",
})

# ---------------------------------------------------------------------------
# Tools denied by default (destructive operations)
# ---------------------------------------------------------------------------

DEFAULT_DENY_TOOLS: frozenset[str] = frozenset({
    "DeleteTool",
    "ExecuteTool",
    "Bash",
    "PowerShell",
})

# ---------------------------------------------------------------------------
# Helper: Build default deny rules
# ---------------------------------------------------------------------------


def get_default_deny_rules() -> list[PermissionRule]:
    """Build default deny rules from DEFAULT_DENY_TOOLS."""
    return [
        PermissionRule(
            source=RuleSource.POLICY,
            rule_behavior=PermissionBehavior.DENY,
            rule_value=PermissionRuleValue(tool_name=name),
        )
        for name in DEFAULT_DENY_TOOLS
    ]


def get_default_allow_rules() -> list[PermissionRule]:
    """Build default allow rules from SAFE_TOOLS."""
    return [
        PermissionRule(
            source=RuleSource.DEFAULT,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name=name),
        )
        for name in SAFE_TOOLS
    ]


# ---------------------------------------------------------------------------
# Path safety checks (adapted from Claude Code's isDangerousFilePath)
# ---------------------------------------------------------------------------


def is_dangerous_path(path: str) -> bool:
    """Check if a file path is dangerous to auto-edit without permission.

    Checks:
    - Dangerous files (.gitconfig, .bashrc, etc.)
    - Dangerous directories (.git, .ssh, .claude, etc.)
    - Shell configuration files
    """
    p = Path(path).resolve()
    path_lower = p.name.lower()

    # Check dangerous file names
    if path_lower in {f.lower() for f in DANGEROUS_FILES}:
        return True

    # Check if path is within dangerous directories
    for part in p.parts:
        if part.lower() in {d.lower() for d in DANGEROUS_DIRECTORIES}:
            return True

    return False


def is_dangerous_bash_command(command: str) -> tuple[bool, str | None]:
    """Check if a bash command matches dangerous patterns.

    Returns:
        (is_dangerous, matched_pattern) — matched_pattern is the pattern that matched

    Adapted from Claude Code's isDangerousBashPermission().
    """
    cmd_lower = command.lower().strip()

    for pattern in DANGEROUS_BASH_PATTERNS:
        # Exact match
        if cmd_lower == pattern:
            return True, pattern
        # Prefix match (command starts with dangerous pattern)
        if cmd_lower.startswith(pattern + " ") or cmd_lower.startswith(pattern + ":"):
            return True, pattern
        # Wildcard prefix
        if cmd_lower.startswith(pattern):
            return True, pattern

    return False, None


# ---------------------------------------------------------------------------
# Permission suggestions (adapted from Claude Code's generateSuggestions)
# ---------------------------------------------------------------------------


def suggest_allow_directory_rule(directory: str) -> dict[str, Any]:
    """Generate a permission update suggestion to allow a directory.

    Mirrors Claude Code's createReadRuleSuggestion().
    """
    return {
        "type": "addRules",
        "rules": [{"toolName": "FileReadTool", "ruleContent": f"{directory}/**"}],
        "behavior": "allow",
        "destination": "session",
    }


def suggest_set_mode(mode: str = "accept_edits") -> dict[str, Any]:
    """Generate a permission update suggestion to change mode."""
    return {
        "type": "setMode",
        "mode": mode,
        "destination": "session",
    }