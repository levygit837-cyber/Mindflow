"""Reviewer agent interfaces.

Defines contracts for code review, quality assessment,
and security evaluation operations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class Reviewer(Protocol):
    """Contract for reviewer agent implementations."""
    
    async def review_session_window(
        self,
        task: Any,  # ReviewTask
        context: Any,  # ReviewExecutionContext
    ) -> dict[str, Any]:
        """Review a session window for insights and actions."""
        ...

    async def assess_quality(self, content: str) -> dict[str, Any]:
        """Assess quality of provided content."""
        ...

    async def security_review(self, code: str) -> dict[str, Any]:
        """Perform security review of code."""
        ...

    async def generate_recommendations(self, analysis: dict) -> list[str]:
        """Generate actionable recommendations from analysis."""
        ...
