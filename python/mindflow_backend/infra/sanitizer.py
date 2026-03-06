"""Input sanitization utilities (Layer 2).

Provides ``sanitize_message(text)`` which applies:
1. Null-byte and control-character stripping (preserving ``\\n`` and ``\\t``)
2. Unicode NFKC normalization
3. HTML tag stripping
4. Basic SQL injection pattern rejection (defense-in-depth)
"""

from __future__ import annotations

import re
import unicodedata

# Control characters we want to strip (U+0000–U+001F) EXCEPT \n (0x0A) and \t (0x09).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Simple HTML tag stripper.
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Basic SQL injection patterns (defense-in-depth — not a primary guard).
_SQL_PATTERNS = [
    re.compile(r"(?i)\b(union\s+select|drop\s+table|insert\s+into|delete\s+from)\b"),
    re.compile(r"(?i);\s*(drop|alter|truncate|exec)\b"),
    re.compile(r"(?i)'\s*(or|and)\s+'?\d*'?\s*=\s*'?\d*"),
]


class SanitizationError(ValueError):
    """Raised when input contains suspicious patterns that cannot be sanitized."""


def sanitize_message(text: str) -> str:
    """Sanitize user input before processing.

    Args:
        text: Raw user message.

    Returns:
        Cleaned text.

    Raises:
        SanitizationError: If input matches known SQL injection patterns.
    """
    # 1. Strip control characters (keep \n and \t).
    text = _CONTROL_CHAR_RE.sub("", text)

    # 2. Unicode NFKC normalization (prevents visual spoofing).
    text = unicodedata.normalize("NFKC", text)

    # 3. Strip HTML tags.
    text = _HTML_TAG_RE.sub("", text)

    # 4. SQL injection pattern check (defense-in-depth).
    for pattern in _SQL_PATTERNS:
        if pattern.search(text):
            raise SanitizationError(
                "Input contains suspicious patterns and was rejected."
            )

    return text
