"""Shared memory types.

Common types used across all memory implementations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MemoryRetrievalResult:
    """Result from memory retrieval operations."""

    context: str
    references: list[str]
