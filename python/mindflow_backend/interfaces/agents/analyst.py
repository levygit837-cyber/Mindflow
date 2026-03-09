"""Analyst agent interface.

Defines contracts for code analysis, system evaluation,
and technical assessment operations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class Analyst(Protocol):
    """Contract for analyst agent implementations."""
    
    async def analyze_code(self, code: str, context: dict) -> dict[str, Any]:
        """Analyze code structure and quality."""
        ...

    async def evaluate_system(self, system_description: str) -> dict[str, Any]:
        """Evaluate system architecture and design."""
        ...

    async def generate_insights(self, data: Any) -> list[str]:
        """Generate analytical insights from data."""
        ...
