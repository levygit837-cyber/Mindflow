"""Analyst agent mode and output schemas.

Defines fast/deep analysis modes and confidence threshold routing
as specified in agent-team-extended-contracts.md.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AnalysisMode(StrEnum):
    """Analyst execution mode."""

    FAST = "fast"
    DEEP = "deep"


class AnalystOutput(BaseModel):
    """Structured output from the Analyst agent."""

    summary: str
    context_files_read: list[str] = Field(default_factory=list)
    symbol_map: dict[str, list[str]] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    suggested_model: str = "flash"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    analysis_mode: AnalysisMode = AnalysisMode.FAST

    def should_deliver_directly(self) -> bool:
        """Confidence >= 0.85: deliver answer directly."""
        return self.confidence >= 0.85

    def should_deliver_with_caveats(self) -> bool:
        """0.60 <= confidence < 0.85: deliver with caveats."""
        return 0.60 <= self.confidence < 0.85

    def should_escalate(self) -> bool:
        """Confidence < 0.60: escalate to Researcher or human."""
        return self.confidence < 0.60
