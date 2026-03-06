"""Tests for input sanitizer (L2)."""

from __future__ import annotations

import pytest

from mindflow_backend.infra.sanitizer import SanitizationError, sanitize_message


def test_strips_control_characters():
    text = "Hello\x00World\x01!\x07"
    result = sanitize_message(text)
    assert result == "HelloWorld!"


def test_preserves_newlines_and_tabs():
    text = "Line1\nLine2\tTabbed"
    result = sanitize_message(text)
    assert result == "Line1\nLine2\tTabbed"


def test_normalizes_unicode_nfkc():
    # Fullwidth 'A' (U+FF21) should become regular 'A'
    text = "\uff21\uff22\uff23"
    result = sanitize_message(text)
    assert result == "ABC"


def test_strips_html_tags():
    text = 'Hello <script>alert("xss")</script>World'
    result = sanitize_message(text)
    assert result == 'Hello alert("xss")World'


def test_rejects_union_select_injection():
    with pytest.raises(SanitizationError):
        sanitize_message("Get me data UNION SELECT * FROM users")


def test_rejects_drop_table_injection():
    with pytest.raises(SanitizationError):
        sanitize_message("'; DROP TABLE users; --")


def test_rejects_or_1_equals_1_injection():
    with pytest.raises(SanitizationError):
        sanitize_message("admin' OR '1'='1")


def test_allows_normal_text():
    text = "What is the weather like today? Please search for the latest news."
    result = sanitize_message(text)
    assert result == text


def test_allows_code_snippets():
    text = "def hello():\n    print('Hello, World!')\n    return True"
    result = sanitize_message(text)
    assert result == text
