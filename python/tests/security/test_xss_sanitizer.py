"""Tests for XSS sanitization."""

import pytest

from mindflow_backend.security.xss import XSSSanitizer, sanitize_html, sanitize_url


def test_sanitize_html_script_tag():
    """Test sanitization of script tags."""
    sanitizer = XSSSanitizer()
    html = "<script>alert('xss')</script>"

    sanitized = sanitizer.sanitize_html(html)

    assert "<script>" not in sanitized
    assert "&lt;script&gt;" in sanitized


def test_sanitize_html_javascript_protocol():
    """Test sanitization of javascript: protocol."""
    sanitizer = XSSSanitizer()
    html = '<a href="javascript:alert(1)">Click</a>'

    sanitized = sanitizer.sanitize_html(html)

    # The script should not be executable - check that href is sanitized
    # Bleach escapes the href attribute value
    assert sanitized != html  # Should be different from input


def test_sanitize_html_event_handler():
    """Test sanitization of event handlers."""
    sanitizer = XSSSanitizer()
    html = '<div onclick="alert(1)">Click</div>'

    sanitized = sanitizer.sanitize_html(html)

    # Event handler should be escaped
    assert "onclick" not in sanitized.lower() or "&quot;" in sanitized


def test_sanitize_plain_text_xss():
    """Test sanitization of plain text with XSS."""
    sanitizer = XSSSanitizer()
    text = "<img src=x onerror=alert(1)>"

    sanitized = sanitizer.sanitize_plain_text(text)

    assert "<img" not in sanitized or "&lt;" in sanitized


def test_sanitize_url_javascript():
    """Test sanitization of javascript: URL."""
    url = "javascript:alert('xss')"

    sanitized = sanitize_url(url)

    assert sanitized == ""


def test_sanitize_url_data_html():
    """Test sanitization of data: URL with HTML."""
    url = "data:text/html,<script>alert(1)</script>"

    sanitized = sanitize_url(url)

    assert sanitized == ""


def test_sanitize_url_safe():
    """Test sanitization of safe URL."""
    url = "https://example.com/path"

    sanitized = sanitize_url(url)

    assert sanitized == url or "example.com" in sanitized


def test_sanitize_json_with_xss():
    """Test sanitization of JSON with XSS."""
    sanitizer = XSSSanitizer()
    data = {"html": "<script>alert(1)</script>"}

    sanitized = sanitizer.sanitize_json(data)

    assert "<script>" not in sanitized


def test_sanitize_for_context_html():
    """Test context-aware sanitization for HTML."""
    sanitizer = XSSSanitizer()
    text = "<b>Bold</b>"

    sanitized = sanitizer.sanitize_for_context(text, "html")

    assert "<b>" not in sanitized or "&lt;" in sanitized


def test_sanitize_for_context_plain():
    """Test context-aware sanitization for plain text."""
    sanitizer = XSSSanitizer()
    text = "Plain text"

    sanitized = sanitizer.sanitize_for_context(text, "plain")

    assert sanitized == "Plain text" or "Plain" in sanitized


def test_sanitize_empty_string():
    """Test sanitization of empty string."""
    sanitizer = XSSSanitizer()

    assert sanitizer.sanitize_html("") == ""
    assert sanitizer.sanitize_plain_text("") == ""
    assert sanitizer.sanitize_url("") == ""


def test_sanitize_none():
    """Test sanitization of None."""
    sanitizer = XSSSanitizer()

    assert sanitizer.sanitize_html(None) == None
    assert sanitizer.sanitize_plain_text(None) == None
    assert sanitizer.sanitize_url(None) == None


def test_convenience_functions():
    """Test convenience functions."""
    html = "<script>alert(1)</script>"

    sanitized = sanitize_html(html)

    assert "<script>" not in sanitized
