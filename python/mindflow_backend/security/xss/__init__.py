"""XSS sanitization module.

Provides input/output sanitization to prevent XSS attacks.
"""

from .sanitizer import XSSSanitizer, sanitize_html, sanitize_json, sanitize_url

__all__ = [
    "XSSSanitizer",
    "sanitize_html",
    "sanitize_json",
    "sanitize_url",
]
