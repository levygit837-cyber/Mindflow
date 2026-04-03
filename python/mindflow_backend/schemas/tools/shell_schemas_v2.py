"""Enhanced shell/bash tool schemas for MindFlow backend (v2).

Provides comprehensive schemas for shell execution with security validators,
permission system, and command analysis matching Claude Code standards.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


class CommandSemanticType(str, Enum):
    """Semantic type of shell command."""

    READ = "read"  # Read-only operations (cat, ls, grep)
    WRITE = "write"  # Write operations (echo >, cp, mv)
    EXECUTE = "execute"  # Execution operations (python, node)
    SEARCH = "search"  # Search operations (find, grep, rg)
    GIT = "git"  # Git operations
    NETWORK = "network"  # Network operations (curl, wget)
    SYSTEM = "system"  # System operations (ps, top, df)
    DANGEROUS = "dangerous"  # Dangerous operations (rm, dd, mkfs)
    UNKNOWN = "unknown"  # Unknown/unclassified


class BashSecurityLevel(str, Enum):
    """Security level for bash commands."""

    SAFE = "safe"  # Safe read-only commands
    MODERATE = "moderate"  # Commands that modify files
    DANGEROUS = "dangerous"  # Potentially destructive commands
    CRITICAL = "critical"  # Extremely dangerous commands


# ============================================================================
# ShellExecutorTool Schema (Enhanced)
# ============================================================================

class ShellExecuteInput(BaseModel):
    """Input schema for ShellExecutorTool."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    command: str = Field(..., description="Shell command to execute")
    timeout: int = Field(default=30, description="Timeout in seconds", ge=1, le=600)
    working_dir: str | None = Field(
        None,
        description="Working directory",
        validation_alias=AliasChoices("working_dir", "cwd"),
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
        validation_alias=AliasChoices("environment", "env"),
    )
    capture_output: bool = Field(default=True, description="Capture command output")
    shell: bool = Field(default=True, description="Use system shell")
    check_return_code: bool = Field(default=False, description="Check return code for success")
    run_in_background: bool = Field(default=False, description="Run command in background")
    sandbox_mode: str | None = Field(default=None, description="Sandbox mode for security validation")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate command is not empty."""
        if not v or not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is reasonable."""
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        if v > 600:
            raise ValueError("Timeout cannot exceed 600 seconds (10 minutes)")
        return v


class ShellExecuteOutput(BaseModel):
    """Output schema for ShellExecutorTool."""

    output: str = Field(..., description="Command output (stdout + stderr)")
    exit_code: int = Field(..., description="Command exit code")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    is_truncated: bool = Field(default=False, description="Whether output was truncated")
    semantic_type: CommandSemanticType | None = Field(None, description="Semantic type of command")
    security_level: BashSecurityLevel | None = Field(None, description="Security level")
    background_task_id: str | None = Field(None, description="Background task ID if run_in_background=True")


ShellExecutorInput = ShellExecuteInput


SHELL_EXECUTOR_SCHEMA_V2 = ToolSchema(
    name="shell_execute",
    description="Execute shell commands with comprehensive security validation and analysis",
    category="system",
    parameters=[
        ToolParameter(
            name="command",
            type="string",
            description="Shell command to execute",
            required=True
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Timeout in seconds",
            required=False,
            default=30,
            constraints={"minimum": 1, "maximum": 600}
        ),
        ToolParameter(
            name="working_dir",
            type="string",
            description="Working directory",
            required=False,
            format="directory-path"
        ),
        ToolParameter(
            name="environment",
            type="object",
            description="Environment variables",
            required=False
        ),
        ToolParameter(
            name="capture_output",
            type="boolean",
            description="Capture command output",
            required=False,
            default=True
        ),
        ToolParameter(
            name="shell",
            type="boolean",
            description="Use system shell",
            required=False,
            default=True
        ),
        ToolParameter(
            name="check_return_code",
            type="boolean",
            description="Check return code for success",
            required=False,
            default=False
        ),
        ToolParameter(
            name="run_in_background",
            type="boolean",
            description="Run command in background",
            required=False,
            default=False
        ),
    ],
    returns={
        "type": "object",
        "description": "Shell execution result",
        "properties": {
            "output": {"type": "string"},
            "exit_code": {"type": "integer"},
            "execution_time_ms": {"type": "integer"},
            "is_truncated": {"type": "boolean"},
            "semantic_type": {"type": "string"},
            "security_level": {"type": "string"},
        }
    },
    requires_sandbox=True,
    version="2.0.0"
)


# ============================================================================
# Bash Security Validation Schemas
# ============================================================================

class BashValidationResult(BaseModel):
    """Result of bash security validation."""

    is_safe: bool = Field(..., description="Whether command is safe")
    validator_name: str = Field(..., description="Name of validator that produced this result")
    severity: str = Field(..., description="Severity: info/warning/error/critical")
    message: str | None = Field(None, description="Validation message")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions for fixing issues")
    blocked_patterns: list[str] = Field(default_factory=list, description="Patterns that were blocked")


class BashCommandAnalysis(BaseModel):
    """Analysis of bash command structure."""

    original_command: str = Field(..., description="Original command")
    base_command: str | None = Field(None, description="Base command (first word)")
    subcommands: list[str] = Field(default_factory=list, description="Subcommands")
    arguments: list[str] = Field(default_factory=list, description="Command arguments")
    redirects: list[dict[str, str]] = Field(default_factory=list, description="Redirects (>, >>, <)")
    pipes: list[str] = Field(default_factory=list, description="Piped commands")
    environment_vars: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    semantic_type: CommandSemanticType = Field(default=CommandSemanticType.UNKNOWN, description="Semantic type")
    security_level: BashSecurityLevel = Field(default=BashSecurityLevel.MODERATE, description="Security level")
    is_read_only: bool = Field(default=False, description="Whether command is read-only")
    validation_results: list[BashValidationResult] = Field(default_factory=list, description="Validation results")


class BashSecurityPolicy(BaseModel):
    """Security policy for bash execution."""

    allow_dangerous_commands: bool = Field(default=False, description="Allow dangerous commands")
    allow_network_access: bool = Field(default=True, description="Allow network access")
    allow_file_write: bool = Field(default=True, description="Allow file write operations")
    allow_sudo: bool = Field(default=False, description="Allow sudo commands")
    allow_eval: bool = Field(default=False, description="Allow eval-like commands")
    max_command_length: int = Field(default=10000, description="Maximum command length")
    blocked_commands: list[str] = Field(default_factory=list, description="Explicitly blocked commands")
    allowed_commands: list[str] = Field(default_factory=list, description="Explicitly allowed commands")
    require_confirmation: list[str] = Field(default_factory=list, description="Commands requiring confirmation")


# ============================================================================
# Bash Validator Schemas
# ============================================================================

class ValidatorConfig(BaseModel):
    """Configuration for a bash validator."""

    validator_id: str = Field(..., description="Unique validator identifier")
    name: str = Field(..., description="Validator name")
    description: str = Field(..., description="Validator description")
    enabled: bool = Field(default=True, description="Whether validator is enabled")
    priority: int = Field(default=0, description="Validator priority (higher = runs first)")
    is_security_check: bool = Field(default=True, description="Whether this is a security check")


# Predefined validators (to be implemented in Phase 3)
BASH_VALIDATORS = [
    ValidatorConfig(
        validator_id="command_injection",
        name="Command Injection Validator",
        description="Detects command injection via metacharacters",
        priority=100,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="path_traversal",
        name="Path Traversal Validator",
        description="Detects path traversal attempts",
        priority=100,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="dangerous_commands",
        name="Dangerous Commands Validator",
        description="Blocks dangerous commands (rm -rf, dd, mkfs, etc.)",
        priority=100,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="eval_like",
        name="Eval-like Commands Validator",
        description="Detects eval, exec, source commands",
        priority=100,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="newline_injection",
        name="Newline Injection Validator",
        description="Detects newline injection attacks",
        priority=90,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="carriage_return",
        name="Carriage Return Validator",
        description="Detects CR injection attacks",
        priority=90,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="ifs_injection",
        name="IFS Injection Validator",
        description="Detects IFS manipulation",
        priority=90,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="control_characters",
        name="Control Characters Validator",
        description="Detects non-printable control characters",
        priority=90,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="malformed_tokens",
        name="Malformed Token Validator",
        description="Detects malformed tokens with command separators",
        priority=80,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="shell_quote_bugs",
        name="Shell Quote Bug Validator",
        description="Detects shell-quote parsing bugs",
        priority=80,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="brace_expansion",
        name="Brace Expansion Validator",
        description="Validates brace expansion patterns",
        priority=70,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="heredoc_validation",
        name="Heredoc Validator",
        description="Validates heredoc syntax",
        priority=70,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="zsh_dangerous",
        name="Zsh Dangerous Commands Validator",
        description="Blocks Zsh-specific dangerous commands",
        priority=100,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="jq_system",
        name="jq system() Validator",
        description="Detects jq system() function",
        priority=80,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="curl_wget_flags",
        name="curl/wget Flags Validator",
        description="Validates curl/wget dangerous flags",
        priority=70,
        is_security_check=True
    ),
    ValidatorConfig(
        validator_id="git_operations",
        name="Git Operations Validator",
        description="Validates git operations",
        priority=50,
        is_security_check=False
    ),
]


# ============================================================================
# Read-Only Command Detection
# ============================================================================

READ_ONLY_COMMANDS = {
    # File reading
    "cat", "head", "tail", "less", "more", "grep", "rg", "ag", "ack",
    # Directory listing
    "ls", "tree", "du", "find",
    # File info
    "stat", "file", "wc", "strings",
    # Git read-only
    "git status", "git diff", "git log", "git show", "git blame",
    # System info
    "ps", "top", "df", "free", "uptime", "uname",
    # Data processing (read-only when used correctly)
    "jq", "awk", "cut", "sort", "uniq", "tr",
}

WRITE_COMMANDS = {
    # File operations
    "rm", "mv", "cp", "touch", "mkdir", "rmdir",
    # File writing
    "echo", "printf", "tee",
    # Editors
    "vim", "nano", "emacs", "sed",
    # Git write
    "git add", "git commit", "git push", "git pull", "git merge",
    # Compression
    "tar", "zip", "unzip", "gzip", "gunzip",
}

DANGEROUS_COMMANDS = {
    # Destructive
    "rm -rf", "dd", "mkfs", "fdisk", "format",
    # System control
    "shutdown", "reboot", "halt", "poweroff",
    # Privilege escalation
    "sudo", "su",
    # Eval-like
    "eval", "exec", "source",
}


# Export all schemas
SHELL_SCHEMAS_V2 = {
    "shell_execute": SHELL_EXECUTOR_SCHEMA_V2,
}
