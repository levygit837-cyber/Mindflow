"""Tests for Secret Scanner implementation."""

import pytest
from pathlib import Path
import tempfile

from mindflow_backend.security.secrets.scanner import SecretScanner, SecretMatch


def test_secret_scanner_anthropic_key():
    """Test detection of Anthropic API key."""
    scanner = SecretScanner()
    content = "API_KEY = 'sk-ant-api03-' + 'A' * 93 + 'AA'"

    matches = scanner.scan_content(content)

    assert len(matches) > 0
    assert any(m.secret_type == "anthropic_api_key" for m in matches)
    assert matches[0].severity == "critical"


def test_secret_scanner_openai_key():
    """Test detection of OpenAI API key."""
    scanner = SecretScanner()
    content = "OPENAI_KEY = 'sk-' + 'A' * 48"

    matches = scanner.scan_content(content)

    assert len(matches) > 0
    assert any(m.secret_type == "openai_api_key" for m in matches)


def test_secret_scanner_aws_credentials():
    """Test detection of AWS credentials."""
    scanner = SecretScanner()
    content = """
    AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'
    AWS_SECRET_ACCESS_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    """

    matches = scanner.scan_content(content)

    assert len(matches) >= 2
    assert any(m.secret_type == "aws_access_key" for m in matches)
    assert any(m.secret_type == "aws_secret_key" for m in matches)


def test_secret_scanner_github_token():
    """Test detection of GitHub tokens."""
    scanner = SecretScanner()
    content = "GITHUB_TOKEN = 'ghp_' + 'A' * 36"

    matches = scanner.scan_content(content)

    assert len(matches) > 0
    assert any(m.secret_type == "github_pat" for m in matches)


def test_secret_scanner_database_url():
    """Test detection of database connection strings."""
    scanner = SecretScanner()
    content = "DATABASE_URL = 'postgresql://user:password@localhost:5432/db'"

    matches = scanner.scan_content(content)

    assert len(matches) > 0
    assert any(m.secret_type == "postgres_url" for m in matches)


def test_secret_scanner_private_key():
    """Test detection of private keys."""
    scanner = SecretScanner()
    content = """
    -----BEGIN RSA PRIVATE KEY-----
    MIIEpAIBAAKCAQEA...
    -----END RSA PRIVATE KEY-----
    """

    matches = scanner.scan_content(content)

    assert len(matches) > 0
    assert any(m.secret_type == "rsa_private_key" for m in matches)


def test_secret_scanner_jwt_token():
    """Test detection of JWT tokens."""
    scanner = SecretScanner()
    content = "TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'"

    matches = scanner.scan_content(content)

    assert len(matches) > 0
    assert any(m.secret_type == "jwt_token" for m in matches)


def test_secret_scanner_multiple_secrets():
    """Test detection of multiple secrets in one file."""
    scanner = SecretScanner()
    content = """
    OPENAI_KEY = 'sk-' + 'A' * 48
    GITHUB_TOKEN = 'ghp_' + 'B' * 36
    DATABASE_URL = 'postgresql://user:pass@localhost/db'
    """

    matches = scanner.scan_content(content)

    assert len(matches) >= 3


def test_secret_scanner_line_numbers():
    """Test line number tracking."""
    scanner = SecretScanner()
    content = """line 1
line 2
API_KEY = 'sk-ant-api03-' + 'A' * 93 + 'AA'
line 4"""

    matches = scanner.scan_content(content)

    assert len(matches) > 0
    assert matches[0].line_number == 3


def test_secret_scanner_scan_file():
    """Test scanning a file."""
    scanner = SecretScanner()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("API_KEY = 'sk-ant-api03-' + 'A' * 93 + 'AA'\n")
        temp_path = f.name

    try:
        matches = scanner.scan_file(temp_path)
        assert len(matches) > 0
        assert matches[0].file_path == temp_path
    finally:
        Path(temp_path).unlink()


def test_secret_scanner_format_report():
    """Test report formatting."""
    scanner = SecretScanner()
    content = "API_KEY = 'sk-ant-api03-' + 'A' * 93 + 'AA'"

    matches = scanner.scan_content(content)
    report = scanner.format_report(matches)

    assert "CRITICAL" in report
    assert "anthropic_api_key" in report


def test_secret_scanner_no_secrets():
    """Test clean file with no secrets."""
    scanner = SecretScanner()
    content = """
    def hello_world():
        print("Hello, World!")
    """

    matches = scanner.scan_content(content)
    report = scanner.format_report(matches)

    assert len(matches) == 0
    assert "No secrets detected" in report


def test_secret_scanner_severity_levels():
    """Test different severity levels."""
    scanner = SecretScanner()
    content = """
    API_KEY = 'sk-ant-api03-' + 'A' * 93 + 'AA'  # critical
    PASSWORD = "mypassword123"  # medium
    """

    matches = scanner.scan_content(content)

    critical = [m for m in matches if m.severity == "critical"]
    medium = [m for m in matches if m.severity == "medium"]

    assert len(critical) > 0
    assert len(medium) > 0
