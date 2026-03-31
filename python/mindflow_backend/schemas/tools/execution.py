"""Tool execution modes for MindFlow.

Mirrors the Claude Code CLI tool execution behaviors:
- acceptsEdits: Destructive tools (Edit, Write, Bash) — always requires permission
- ask: Tools requiring interactive approval before execution
- bypass: Read-only tools or sandbox-only — executes without permission prompt

These modes are derived from a tool's metadata (is_read_only, is_destructive, etc.)
but can also be explicitly set when registering a tool.
"""

from __future__ import annotations

from enum import StrEnum


class ToolExecutionMode(StrEnum):
    """How a tool is executed — mirrors Claude Code's tool behaviors.

    Each mode determines:
    - Whether a permission check is required before execution
    - Whether the tool can modify the filesystem or external state
    - How the tool appears in the model's tool list (deferred vs always-available)

    Mode derivation from tool metadata:
    - is_destructive=True → ACCEPTS_EDITS (always requires permission)
    - is_read_only=True → BYPASS (no permission needed, safe to run)
    - Neither set (default) → ASK (interactive approval required)

    Usage:
        tool = build_tool(
            name="FileEditTool",
            execute=edit_file,
            is_destructive=True,    # → ACCEPTS_EDITS
        )
    """

    # -- Destructive tools (Edits, Writes, Bash) --
    ACCEPTS_EDITS = "accepts_edits"
    """Tool potentially modifies state (files, system, network).
    
    Mirrors Claude Code's behavior for Edit, Write, Bash:
    - Always requires explicit user permission (unless mode=bypass)
    - Appears as a destructive action in the model's tool list
    - Subject to deny rules regardless of allow rules (safety net)
    
    Examples: FileEditTool, FileWriteTool, BashTool, NotebookEditTool
    """

    # -- Interactive approval tools --
    ASK = "ask"
    """Tool requires interactive user approval before execution.
    
    Used when:
    - Tool is neither read-only nor destructive (ambiguous intent)
    - Tool has side effects that require context to evaluate
    - Policy requires human oversight for this category
    
    In auto/sandbox mode: may be automatically allowed by classifier/hook.
    In default mode: always prompts user.
    In bypass mode: executes without approval.
    
    Examples: WebFetchTool, ToolSearchTool, MCP tools (by default)
    """

    # -- No approval needed (Read-only, Safety-checked) --
    BYPASS = "bypass"
    """Tool executes without permission prompting.
    
    Used when:
    - Tool is definitively read-only (Read, Grep, Glob)
    - Tool runs in a verified sandbox with no external access
    - Tool is essential for system operation (status, help)
    
    Still subject to deny rules (can be blocked by policy).
    In non-sandbox environments: only truly read-only tools should use this.
    
    Examples: FileReadTool, GrepTool, GlobTool, TodoReadTool
    """

    @property
    def requires_permission(self) -> bool:
        """Whether this mode requires a permission check before execution.

        Returns False only for BYPASS (always safe to run).
        ACCEPTS_EDITS and ASK both require permission — the difference is:
        - ACCEPTS_EDITS: Permission model is always 'ask user' (no auto-allow)
        - ASK: Permission may be auto-allowed by classifier/hook in auto mode
        """
        return self != ToolExecutionMode.BYPASS

    @property
    def is_destructive_mode(self) -> bool:
        """Whether this mode implies destructive/capability-of-modifying actions."""
        return self == ToolExecutionMode.ACCEPTS_EDITS

    @property
    def is_safe_mode(self) -> bool:
        """Whether this mode implies no external state modification."""
        return self == ToolExecutionMode.BYPASS