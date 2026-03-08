"""Output categorization helpers for streaming metadata.

This module is used by the stream normalizer to tag response chunks with a
high-level category. It is intentionally lightweight and dependency-free.
"""

from __future__ import annotations


def categorize_output(text: str) -> str:
    """Categorize LLM output for UI/telemetry purposes."""
    t = (text or "").strip().lower()
    if not t:
        return "empty"
    if t.startswith("{") or t.startswith("["):
        return "json_like"
    if "```" in t:
        return "code"
    if t.startswith("error") or "exception" in t:
        return "error"
    return "text"

