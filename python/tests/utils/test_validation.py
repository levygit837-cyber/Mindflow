"""Test cases for validation utilities."""

import pytest
from mindflow_backend.utils.validation import (
    validate_email,
    validate_url,
    validate_phone,
    validate_uuid,
    sanitize_string,
    sanitize_html,
    validate_json_structure,
)


class TestValidationUtilities:
    """Test validation utility functions."""

    def test_validate_email(self):
        """Test email validation."""
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.co.uk") is True
        assert validate_email("invalid-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("test@") is False

    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://www.example.com") is True
        assert validate_url("http://localhost:8000") is True
        assert validate_url("ftp://files.server.com") is True
        assert validate_url("not-a-url") is False
        assert validate_url("http://") is False

    def test_validate_phone(self):
        """Test phone number validation."""
        assert validate_phone("+55 11 98765-4321") is True
        assert validate_phone("(11) 98765-4321") is True
        assert validate_phone("11987654321") is True
        assert validate_phone("123") is False
        assert validate_phone("") is False

    def test_validate_uuid(self):
        """Test UUID validation."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_uuid(valid_uuid) is True
        assert validate_uuid("invalid-uuid") is False
        assert validate_uuid("550e8400-e29b-41d4") is False  # Too short

    def test_sanitize_string(self):
        """Test string sanitization."""
        assert sanitize_string("Hello <script>alert('xss')</script> World") == "Hello alertxss World"
        assert sanitize_string("Normal text") == "Normal text"
        assert sanitize_string("") == ""

    def test_sanitize_html(self):
        """Test HTML sanitization."""
        html = "<p>Hello <b>world</b>!</p>"
        result = sanitize_html(html)
        assert "Hello world!" in result
        assert "<p>" not in result
        assert "<b>" not in result

    def test_validate_json_structure(self):
        """Test JSON structure validation."""
        valid_schema = {"name": str, "age": int}
        valid_data = {"name": "John", "age": 30}
        assert validate_json_structure(valid_data, valid_schema) is True

        invalid_data = {"name": "John", "age": "thirty"}
        assert validate_json_structure(invalid_data, valid_schema) is False

    def test_validate_email_edge_cases(self):
        """Test email validation edge cases."""
        assert validate_email("test+tag@example.com") is True
        assert validate_email("test@sub.domain.com") is True
        assert validate_email("test@domain") is False  # No TLD

    def test_sanitize_string_special_chars(self):
        """Test sanitization of special characters."""
        text = "Hello\x00\x01\x02World"
        result = sanitize_string(text)
        assert "HelloWorld" == result

    def test_validate_json_structure_nested(self):
        """Test nested JSON structure validation."""
        schema = {"user": {"name": str, "profile": {"age": int}}}
        data = {"user": {"name": "John", "profile": {"age": 30}}}
        assert validate_json_structure(data, schema) is True

        invalid_data = {"user": {"name": "John", "profile": {"age": "thirty"}}}
        assert validate_json_structure(invalid_data, schema) is False
