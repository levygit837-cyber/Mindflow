"""Context governance schemas.

Defines budget configuration, explorer summary contract, context quality
events, and scope partitioning as specified in orchestrator-context-governance.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ContextScope(StrEnum):
    """Context partition scope."""

    SESSION = "session"
    TASK = "task"
    OBJECTIVE = "objective"


class ContextBudgetConfig(BaseModel):
    """Token budget thresholds for context governance."""

    warning_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    enforcement_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    hard_limit_tokens: int = 1_000_000
    max_payload_tokens: int = 10_000
    rollup_oldest_pct: float = Field(default=0.30, ge=0.0, le=1.0)


class ExplorerSummary(BaseModel):
    """Structured summary from Analyst/Researcher to orchestrator.

    The orchestrator receives ONLY this summary, never raw file contents.
    """

    summary: str
    context_files_read: list[str] = Field(default_factory=list)
    key_symbols: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    suggested_next: str = ""


class ContextEventType(StrEnum):
    """Observable context governance events."""

    BUDGET_WARNING = "context_budget_warning"
    BUDGET_ENFORCED = "context_budget_enforced"
    ROLLUP_TRIGGERED = "context_rollup_triggered"
    MEMORY_WINDOW_CREATED = "memory_window_created"
    MEMORY_CONTEXT_LOADED = "memory_context_loaded"
    PAYLOAD_REJECTED = "context_payload_rejected"


class ContextEvent(BaseModel):
    """A trackable context governance event."""

    event_type: ContextEventType
    agent_id: str
    session_id: str
    current_tokens: int = 0
    budget_limit: int = 0
    utilization_pct: float = 0.0
    details: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)