"""Coder agent interfaces.

Defines contracts for code generation, modification,
and implementation operations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class Coder(Protocol):
    """Contract for coder agent implementations."""
    
    async def generate_code(self, requirements: str, context: dict) -> str:
        """Generate code based on requirements."""
        ...

    async def modify_code(self, code: str, modifications: list) -> str:
        """Apply modifications to existing code."""
        ...

    async def review_code(self, code: str) -> dict[str, Any]:
        """Review code for quality and best practices."""
        ...

    async def implement_feature(self, feature_spec: dict) -> dict[str, Any]:
        """Implement a complete feature based on specification."""
        ...
