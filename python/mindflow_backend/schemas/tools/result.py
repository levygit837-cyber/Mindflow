"""Tool result schemas for MindFlow tool execution.

Mirrors Claude Code CLI ToolResult type system:
- ToolResult: generic result wrapper with data + optional messages
- ToolResultBudget: budget tracking for tool result sizes
- ContentReplacement: large result truncation tracking
- ValidationResult: input validation result

Design principles:
- All tool executions return a ToolResult
- Results can include new messages to inject into conversation
- Large results are tracked for budget-based truncation
- Validation failures return clear structured errors
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ResultFormat(StrEnum):
    """Format of tool result content."""

    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    ERROR = "error"


class TruncationReason(StrEnum):
    """Why a tool result was truncated."""

    SIZE_LIMIT = "size_limit"          # Exceeded maxResultSizeChars
    TIMEOUT = "timeout"                # Execution timed out
    MEMORY_LIMIT = "memory_limit"      # Output exceeded memory buffer
    CONTENT_LIMIT = "content_limit"    # Content type limit (e.g., too many files)


# ---------------------------------------------------------------------------
# Validation Schema
# ---------------------------------------------------------------------------


class ValidationResult(BaseModel):
    """Result of tool input validation.

    Mirrors Claude Code's ValidationResult:
    - { result: true } for valid
    - { result: false, message: str, errorCode: number } for invalid
    """

    model_config = {"extra": "ignore", "populate_by_name": True}

    result: bool = Field(
        ...,
        description="Whether validation passed",
    )

    # Only when result is false
    message: str | None = Field(
        default=None,
        description="Error message explaining what went wrong",
    )

    error_code: int | None = Field(
        default=None,
        description="Numeric error code for programmatic handling",
    )

    @classmethod
    def success(cls) -> ValidationResult:
        return cls(result=True)

    @classmethod
    def failure(
        cls,
        message: str,
        error_code: int | None = None,
    ) -> ValidationResult:
        return cls(result=False, message=message, error_code=error_code)


# ---------------------------------------------------------------------------
# Truncation Schema
# ---------------------------------------------------------------------------


class ResultTruncation(BaseModel):
    """Metadata about a truncated tool result."""

    model_config = {"extra": "ignore", "populate_by_name": True}

    was_truncated: bool = Field(
        default=False,
        description="Whether the result was truncated",
    )
    reason: TruncationReason | None = Field(
        default=None,
        description="Why the result was truncated",
    )
    original_size: int | None = Field(
        default=None,
        description="Original size in characters",
    )
    truncated_size: int | None = Field(
        default=None,
        description="Size after truncation",
    )
    file_ref: str | None = Field(
        default=None,
        description="File path where full content was saved",
    )


# ---------------------------------------------------------------------------
# Content Replacement Schema
# ---------------------------------------------------------------------------


class ContentReplacement(BaseModel):
    """Tracks content replacements for tool result budgeting.

    Mirrors Claude Code's contentReplacementState — when a tool result
    exceeds the budget, the content is replaced with a file reference
    and the replacement is tracked.
    """

    model_config = {"extra": "ignore", "populate_by_name": True}

    # Map of UUID → truncated content
    replacements: dict[str, str] = Field(
        default_factory=dict,
        description="Map of replacement IDs to truncated content",
    )

    def add_replacement(self, content: str) -> str:
        """Add a content replacement and return its ID."""
        import uuid
        replacement_id = str(uuid.uuid4())
        self.replacements[replacement_id] = content
        return replacement_id

    def has_replacements(self) -> bool:
        return bool(self.replacements)

    def clear(self) -> None:
        self.replacements.clear()


# ---------------------------------------------------------------------------
# Tool Result Budget Schema
# ---------------------------------------------------------------------------


class ToolResultBudget(BaseModel):
    """Budget configuration for tool results.

    Similar to Claude Code's maxResultSizeChars per tool — tracks how
    large a tool result can be before it's truncated or saved to disk.
    """

    model_config = {"extra": "ignore", "populate_by_name": True}

    # Global budget
    max_chars: int = Field(
        default=100_000,
        ge=0,
        description="Maximum result size in characters",
    )

    # Per-tool budgets (tool_name → max_chars)
    per_tool: dict[str, int] = Field(
        default_factory=dict,
        description="Per-tool max size overrides",
    )

    # Tools exempt from budgeting (e.g., Read, where truncation is circular)
    exempt_tools: set[str] = Field(
        default_factory=set,
        description="Tools exempt from budget limits",
    )

    def get_max_for_tool(self, tool_name: str) -> int | None:
        """Get max result size for a specific tool.
        
        Returns None for exempt tools (no limit).
        """
        # Check exempt first
        for exempt in self.exempt_tools:
            if tool_name.lower() == exempt.lower():
                return None
        # Check per-tool
        for pattern, limit in self.per_tool.items():
            if tool_name.lower() == pattern.lower():
                return limit
        return self.max_chars


# ---------------------------------------------------------------------------
# Main Tool Result Schema
# ---------------------------------------------------------------------------


class ToolResult(BaseModel):
    """Standard tool execution result.

    Mirrors Claude Code's ToolResult<Output> type:
    - data: The actual result data
    - newMessages: Optional messages to inject into conversation
    - mcpMeta: MCP protocol metadata (structuredContent, _meta)

    Plus MindFlow-specific additions:
    - truncation: Metadata if result was truncated
    - timestamp: Execution timestamp
    """

    model_config = {"extra": "ignore", "populate_by_name": True}

    # The actual result data (type varies by tool)
    data: Any = Field(
        default=None,
        description="Tool execution result data",
    )

    # Messages to inject into the conversation (e.g., notification, attachment)
    new_messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Messages to inject into conversation",
    )

    # MCP protocol metadata (for MCP-originated tools)
    mcp_meta: dict[str, Any] | None = Field(
        default=None,
        description="MCP protocol metadata (_meta, structuredContent)",
    )

    # Truncation metadata (if result exceeded budget)
    truncation: ResultTruncation | None = Field(
        default=None,
        description="Truncation metadata if result was cut off",
    )

    # Content replacement tracking (for budget-based truncation)
    content_replacement: ContentReplacement | None = Field(
        default=None,
        description="Content replacements for budget tracking",
    )

    # Execution metadata
    timestamp: str | None = Field(
        default=None,
        description="Execution timestamp (ISO 8601)",
    )

    # Performance metadata
    execution_time_ms: int | None = Field(
        default=None,
        description="Tool execution time in milliseconds",
    )

    # Legacy compatibility fields (deprecated but maintained for backward compatibility)
    success: bool = Field(
        default=True,
        description="Legacy: Whether the tool execution succeeded (deprecated, use truncation.reason)",
    )

    content: str | None = Field(
        default=None,
        description="Legacy: Tool result content as string (deprecated, use data)",
    )

    error_message: str | None = Field(
        default=None,
        description="Legacy: Error message if execution failed (deprecated)",
        alias="error",
    )

    # Legacy metadata field (for backward compatibility with old API)
    legacy_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Legacy: Metadata dict (deprecated, use individual fields)",
        exclude=True,
    )

    @property
    def is_error(self) -> bool:
        """Legacy property for backward compatibility."""
        return not self.success or self.error_message is not None

    @property
    def error(self) -> str | None:
        """Legacy property for backward compatibility."""
        return self.error_message

    @property
    def metadata(self) -> dict[str, Any]:
        """Legacy property for backward compatibility."""
        meta: dict[str, Any] = {}
        if self.truncation:
            meta["truncation"] = self.truncation.model_dump()
        if self.execution_time_ms:
            meta["execution_time_ms"] = self.execution_time_ms
        if self.mcp_meta:
            meta["mcp"] = self.mcp_meta
        if self.legacy_metadata:
            meta.update(self.legacy_metadata)
        return meta

    @model_validator(mode='before')
    @classmethod
    def validate_legacy_params(cls, data: Any) -> Any:
        """Validate and convert legacy parameters to new API."""
        if not isinstance(data, dict):
            return data

        # Convert is_error parameter to success
        if 'is_error' in data:
            is_error = data.pop('is_error')
            data['success'] = not is_error

        # Convert metadata parameter to legacy_metadata
        if 'metadata' in data:
            data['legacy_metadata'] = data.pop('metadata')

        # If content is provided but data is not, sync them
        if 'content' in data and 'data' not in data:
            data['data'] = data['content']

        return data

    def model_post_init(self, __context: Any) -> None:
        """Initialize legacy fields from new API for backward compatibility."""
        # If content is not set but data is, sync them
        if self.content is None and self.data is not None:
            if isinstance(self.data, str):
                self.content = self.data
            else:
                self.content = str(self.data)

    @classmethod
    def create_success(cls, data: Any) -> ToolResult:
        """Create a successful result."""
        return cls(data=data, success=True)

    @classmethod
    def with_messages(cls, data: Any, messages: list[dict[str, Any]]) -> ToolResult:
        """Create a result with injected messages."""
        return cls(data=data, new_messages=messages)

    @classmethod
    def error(
        cls,
        error: str,
        error_code: int | None = None,
    ) -> ToolResult:
        """Create an error result."""
        return cls(
            data=None,
            error_message=error,
            success=False,
            truncation=ResultTruncation(
                was_truncated=False,
                reason=TruncationReason.SIZE_LIMIT,
            ),
        )

    @classmethod
    def truncated(
        cls,
        data: Any,
        reason: TruncationReason = TruncationReason.SIZE_LIMIT,
        original_size: int | None = None,
        truncated_size: int | None = None,
        file_ref: str | None = None,
    ) -> ToolResult:
        """Create a truncated result."""
        return cls(
            data=data,
            truncation=ResultTruncation(
                was_truncated=True,
                reason=reason,
                original_size=original_size,
                truncated_size=truncated_size,
                file_ref=file_ref,
            ),
        )