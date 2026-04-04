"""Tests for Bash validators."""

from mindflow_backend.schemas.tools.tool_permissions import PermissionBehavior, PermissionDecision
from mindflow_backend.security.validators import bash_validators as security_bash_validators
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


def test_security_validator_delegates_to_canonical(monkeypatch):
    """Security-facing validator should delegate to the canonical validator."""
    calls = []

    def _fake_validate(command: str, sandbox_mode: str | None = None) -> PermissionDecision:
        calls.append((command, sandbox_mode))
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="Command passed all security checks",
        )

    monkeypatch.setattr(
        security_bash_validators,
        "_canonical_validate_bash_command",
        _fake_validate,
        raising=False,
    )

    result = security_bash_validators.validate_bash_command("echo 'ok'")

    assert result.behavior == "passthrough"
    assert calls == [("echo 'ok'", None)]


def test_security_validator_preserves_strict_eval_block(monkeypatch):
    """Security-facing validator must keep legacy hard-block behavior for eval-like commands."""

    def _fake_validate(command: str, sandbox_mode: str | None = None) -> PermissionDecision:
        assert command == "eval 'legacy'"
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            message="Eval-like command detected: eval",
            reason="This command executes arbitrary code",
            is_security_check=True,
        )

    monkeypatch.setattr(
        security_bash_validators,
        "_canonical_validate_bash_command",
        _fake_validate,
        raising=False,
    )

    result = security_bash_validators.validate_bash_command("eval 'legacy'")

    assert result.behavior == "block"
    assert result.severity == "high"
