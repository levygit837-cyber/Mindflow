"""Tests for Bash validators."""

from mindflow_backend.security.validators.bash_validators import validate_bash_command


def test_safe_command():
    """Test safe command passes."""
    result = validate_bash_command("ls -la")
    assert result.behavior == "passthrough"


def test_dangerous_command():
    """Test dangerous command blocked."""
    result = validate_bash_command("rm -rf /")
    assert result.behavior == "block"


def test_eval_blocked():
    """Test eval blocked."""
    result = validate_bash_command("eval 'malicious'")
    assert result.behavior == "block"


def test_binary_hijack():
    """Test binary hijack blocked."""
    result = validate_bash_command("LD_PRELOAD=/tmp/evil.so ls")
    assert result.behavior == "block"
