"""XSS sanitizer for input/output sanitization.

Provides context-aware sanitization for different contexts (HTML, JS, CSS, URL).

TODO: Integrate with CLI
- CLI should sanitize all user input before processing
- CLI should sanitize all output before display

TODO: Integrate with Desktop
- Desktop should sanitize all user input before processing
- Desktop should sanitize all output before display
"""

from __future__ import annotations

import html
import json
from typing import Any

from mindflow_backend.infra.logging import get_logger

from .patterns import SAFE_HTML_ATTRIBUTES, SAFE_HTML_TAGS, contains_xss

_logger = get_logger(__name__)


class XSSSanitizer:
    """XSS sanitizer with context-aware sanitization.

    Features:
    - HTML sanitization
    - JSON sanitization
    - URL sanitization
    - Plain text sanitization
    """

    def sanitize_html(self, text: str) -> str:
        """Sanitize HTML content.

        Always escapes HTML entities for security. Does not allow any HTML tags.

        Args:
            text: HTML content to sanitize

        Returns:
            Sanitized HTML content with all HTML entities escaped
        """
        if not text:
            return text

        # Check for XSS patterns
        if contains_xss(text):
            _logger.warning("xss_pattern_detected_in_html")

        # Escape HTML entities
        return html.escape(text)

    def sanitize_json(self, data: dict[str, Any] | list[Any] | str) -> str:
        """Sanitize JSON content.

        Args:
            data: Data to sanitize (dict, list, or JSON string)

        Returns:
            Sanitized JSON string
        """
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                # If not valid JSON, treat as plain text
                return self.sanitize_plain_text(data)
        else:
            parsed = data

        # Recursively sanitize strings in the data structure
        sanitized = self._sanitize_data_structure(parsed)

        return json.dumps(sanitized)

    def _sanitize_data_structure(self, data: Any) -> Any:
        """Recursively sanitize data structure.

        Args:
            data: Data to sanitize

        Returns:
            Sanitized data structure
        """
        if isinstance(data, str):
            return self.sanitize_plain_text(data)
        elif isinstance(data, dict):
            return {key: self._sanitize_data_structure(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data_structure(item) for item in data]
        else:
            return data

    def sanitize_url(self, url: str) -> str:
        """Sanitize URL.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL
        """
        if not url:
            return url

        # Check for javascript: protocol
        if url.lower().startswith("javascript:"):
            _logger.warning("javascript_protocol_detected", url=url)
            return ""

        # Check for data: URLs with HTML/JS
        if url.lower().startswith("data:"):
            if "text/html" in url.lower() or "javascript" in url.lower():
                _logger.warning("dangerous_data_url_detected", url=url)
                return ""

        # Basic URL sanitization
        return html.escape(url)

    def sanitize_plain_text(self, text: str) -> str:
        """Sanitize plain text.

        Args:
            text: Plain text to sanitize

        Returns:
            Sanitized plain text
        """
        if not text:
            return text

        # Check for XSS patterns
        if contains_xss(text):
            _logger.warning("xss_pattern_detected_in_text")

        # Escape HTML entities (prevents HTML injection)
        return html.escape(text)

    def sanitize_for_context(self, text: str, context: str) -> str:
        """Sanitize text for specific context.

        Args:
            text: Text to sanitize
            context: Context (html, js, css, url, plain)

        Returns:
            Sanitized text
        """
        context = context.lower()

        if context == "html":
            return self.sanitize_html(text)
        elif context == "json":
            return self.sanitize_json(text)
        elif context == "url":
            return self.sanitize_url(text)
        else:  # plain, js, css
            return self.sanitize_plain_text(text)


# Global XSS sanitizer instance
_xss_sanitizer: XSSSanitizer | None = None


def get_xss_sanitizer() -> XSSSanitizer:
    """Get global XSS sanitizer instance.

    Returns:
        XSSSanitizer instance
    """
    global _xss_sanitizer
    if _xss_sanitizer is None:
        _xss_sanitizer = XSSSanitizer()
    return _xss_sanitizer


def sanitize_html(text: str) -> str:
    """Convenience function to sanitize HTML.

    Always escapes HTML entities for security. Does not allow any HTML tags.

    Args:
        text: HTML content to sanitize

    Returns:
        Sanitized HTML content with all HTML entities escaped
    """
    sanitizer = get_xss_sanitizer()
    return sanitizer.sanitize_html(text)


def sanitize_json(data: dict[str, Any] | list[Any] | str) -> str:
    """Convenience function to sanitize JSON.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized JSON string
    """
    sanitizer = get_xss_sanitizer()
    return sanitizer.sanitize_json(data)


def sanitize_url(url: str) -> str:
    """Convenience function to sanitize URL.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL
    """
    sanitizer = get_xss_sanitizer()
    return sanitizer.sanitize_url(url)
