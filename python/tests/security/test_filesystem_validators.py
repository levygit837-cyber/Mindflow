"""Unit tests for filesystem security validators.

Tests all filesystem security validators including device file blocking,
symlink validation, TOCTOU protection, path traversal, and secret detection.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.security.filesystem_validators import (
    clear_file_mtime,
    record_file_mtime,
    validate_device_file,
    validate_file_mtime,
    validate_file_size,
    validate_filesystem_operation,
    validate_path_traversal_filesystem,
    validate_secrets,
    validate_symlink,
)
from mindflow_backend.schemas.tools.tool_permissions import PermissionBehavior


class TestDeviceFileBlocking:
    """Test device file blocking validator."""

    def test_regular_file(self):
        """Regular files should pass."""
        decision = validate_device_file("/home/user/file.txt")
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

    def test_dev_zero(self):
        """Reading /dev/zero should be blocked."""
        decision = validate_device_file("/dev/zero")
        assert decision.behavior == PermissionBehavior.DENY
        assert "device" in decision.message.lower()

    def test_dev_random(self):
        """Reading /dev/random should be blocked."""
        decision = validate_device_file("/dev/random")
        assert decision.behavior == PermissionBehavior.DENY

    def test_dev_stdin(self):
        """Reading /dev/stdin should be blocked."""
        decision = validate_device_file("/dev/stdin")
        assert decision.behavior == PermissionBehavior.DENY

    def test_dev_tty(self):
        """Reading /dev/tty should be blocked."""
        decision = validate_device_file("/dev/tty")
        assert decision.behavior == PermissionBehavior.DENY

    def test_proc_fd_stdin(self):
        """Reading /proc/self/fd/0 should be blocked."""
        decision = validate_device_file("/proc/self/fd/0")
        assert decision.behavior == PermissionBehavior.DENY

    def test_proc_fd_stdout(self):
        """Reading /proc/self/fd/1 should be blocked."""
        decision = validate_device_file("/proc/123/fd/1")
        assert decision.behavior == PermissionBehavior.DENY


class TestSymlinkValidation:
    """Test symlink validation."""

    def test_regular_file(self, tmp_path):
        """Regular files should pass."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        decision = validate_symlink(str(file_path))
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

    def test_symlink_within_workspace(self, tmp_path):
        """Symlinks within workspace should pass."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        link = tmp_path / "link.txt"
        link.symlink_to(target)

        decision = validate_symlink(str(link), str(tmp_path))
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

    def test_symlink_outside_workspace(self, tmp_path):
        """Symlinks outside workspace should be blocked."""
        # Create target outside workspace
        with tempfile.TemporaryDirectory() as outside_dir:
            target = Path(outside_dir) / "target.txt"
            target.write_text("content")

            link = tmp_path / "link.txt"
            link.symlink_to(target)

            decision = validate_symlink(str(link), str(tmp_path))
            assert decision.behavior == PermissionBehavior.DENY
            assert "outside workspace" in decision.message.lower()

    def test_symlink_to_etc(self, tmp_path):
        """Symlinks to /etc should be detected."""
        # This test may fail if /etc/passwd doesn't exist or we don't have permission
        # Skip if we can't create the symlink
        try:
            link = tmp_path / "passwd_link"
            link.symlink_to("/etc/passwd")

            decision = validate_symlink(str(link))
            assert decision.behavior == PermissionBehavior.ASK
            assert "sensitive" in decision.message.lower()
        except (OSError, PermissionError):
            pytest.skip("Cannot create symlink to /etc/passwd")


class TestTOCTOUProtection:
    """Test TOCTOU (Time-of-Check-Time-of-Use) protection."""

    def test_file_not_modified(self, tmp_path):
        """File not modified should pass."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        # Record mtime
        mtime = record_file_mtime(str(file_path))
        assert mtime is not None

        # Validate (should pass)
        decision = validate_file_mtime(str(file_path))
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

        # Cleanup
        clear_file_mtime(str(file_path))

    def test_file_modified(self, tmp_path):
        """File modified should be detected."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        # Record mtime
        record_file_mtime(str(file_path))

        # Modify file
        import time
        time.sleep(0.01)  # Ensure mtime changes
        file_path.write_text("modified content")

        # Validate (should fail)
        decision = validate_file_mtime(str(file_path))
        assert decision.behavior == PermissionBehavior.DENY
        assert "modified" in decision.message.lower()

        # Cleanup
        clear_file_mtime(str(file_path))

    def test_no_previous_mtime(self, tmp_path):
        """No previous mtime should pass."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        # Validate without recording (should pass)
        decision = validate_file_mtime(str(file_path))
        assert decision.behavior == PermissionBehavior.PASSTHROUGH


class TestPathTraversal:
    """Test path traversal detection."""

    def test_safe_path(self):
        """Safe paths should pass."""
        decision = validate_path_traversal_filesystem("/home/user/file.txt")
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

    def test_parent_directory_reference(self):
        """../ patterns should be detected."""
        decision = validate_path_traversal_filesystem("/home/user/../../etc/passwd")
        assert decision.behavior == PermissionBehavior.ASK
        assert "parent directory" in decision.message.lower()

    def test_path_within_workspace(self, tmp_path):
        """Paths within workspace should pass."""
        file_path = tmp_path / "subdir" / "file.txt"

        decision = validate_path_traversal_filesystem(str(file_path), str(tmp_path))
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

    def test_path_outside_workspace(self, tmp_path):
        """Paths outside workspace should be blocked."""
        outside_path = "/tmp/outside/file.txt"

        decision = validate_path_traversal_filesystem(outside_path, str(tmp_path))
        assert decision.behavior == PermissionBehavior.DENY
        assert "outside workspace" in decision.message.lower()


class TestSecretDetection:
    """Test secret detection in file content."""

    def test_no_secrets(self):
        """Content without secrets should pass."""
        content = "This is safe content without any secrets."
        decision = validate_secrets(content)
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

    def test_api_key(self):
        """API keys should be detected."""
        content = "API_KEY = 'sk-proj-abcdefghijklmnopqrstuvwxyz1234567890abcdefgh'"
        decision = validate_secrets(content)
        assert decision.behavior == PermissionBehavior.DENY
        assert "secret" in decision.message.lower()

    def test_aws_access_key(self):
        """AWS access keys should be detected."""
        content = "AWS_ACCESS_KEY_ID = AKIAIOSFODNN7EXAMPLE"
        decision = validate_secrets(content)
        assert decision.behavior == PermissionBehavior.DENY

    def test_github_token(self):
        """GitHub tokens should be detected."""
        content = "GITHUB_TOKEN = ghp_abcdefghijklmnopqrstuvwxyz123456"
        decision = validate_secrets(content)
        assert decision.behavior == PermissionBehavior.DENY

    def test_openai_key(self):
        """OpenAI keys should be detected."""
        content = "OPENAI_API_KEY = sk-abcdefghijklmnopqrstuvwxyz1234567890abcdefgh"
        decision = validate_secrets(content)
        assert decision.behavior == PermissionBehavior.DENY

    def test_password(self):
        """Passwords should be detected."""
        content = "password = 'MySecretPassword123!'"
        decision = validate_secrets(content)
        assert decision.behavior == PermissionBehavior.DENY

    def test_private_key(self):
        """Private keys should be detected."""
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
        decision = validate_secrets(content)
        assert decision.behavior == PermissionBehavior.DENY


class TestFileSizeValidation:
    """Test file size validation."""

    def test_small_file(self, tmp_path):
        """Small files should pass."""
        file_path = tmp_path / "small.txt"
        file_path.write_text("small content")

        decision = validate_file_size(str(file_path))
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

    def test_large_file(self, tmp_path):
        """Large files should be blocked."""
        file_path = tmp_path / "large.txt"

        # Create a file larger than 1 GiB (use small limit for testing)
        max_size = 1024  # 1 KB for testing
        file_path.write_bytes(b"x" * (max_size + 1))

        decision = validate_file_size(str(file_path), max_size_bytes=max_size)
        assert decision.behavior == PermissionBehavior.DENY
        assert "too large" in decision.message.lower()


class TestMasterFilesystemValidator:
    """Test master filesystem validator."""

    def test_safe_read_operation(self, tmp_path):
        """Safe read operations should be allowed."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("safe content")

        decision = validate_filesystem_operation(
            str(file_path),
            operation="read",
            workspace_root=str(tmp_path)
        )
        assert decision.behavior == PermissionBehavior.ALLOW

    def test_read_device_file(self):
        """Reading device files should be blocked."""
        decision = validate_filesystem_operation(
            "/dev/zero",
            operation="read"
        )
        assert decision.behavior == PermissionBehavior.DENY

    def test_write_with_secrets(self, tmp_path):
        """Writing secrets should be blocked."""
        file_path = tmp_path / "config.py"
        content = "API_KEY = 'sk-proj-abcdefghijklmnopqrstuvwxyz1234567890abcdefgh'"

        decision = validate_filesystem_operation(
            str(file_path),
            operation="write",
            content=content,
            workspace_root=str(tmp_path),
            check_secrets=True
        )
        assert decision.behavior == PermissionBehavior.DENY
        assert "secret" in decision.message.lower()

    def test_write_safe_content(self, tmp_path):
        """Writing safe content should be allowed."""
        file_path = tmp_path / "file.txt"
        content = "This is safe content"

        decision = validate_filesystem_operation(
            str(file_path),
            operation="write",
            content=content,
            workspace_root=str(tmp_path)
        )
        assert decision.behavior == PermissionBehavior.ALLOW

    def test_path_outside_workspace(self, tmp_path):
        """Accessing paths outside workspace should be blocked."""
        outside_path = "/tmp/outside/file.txt"

        decision = validate_filesystem_operation(
            outside_path,
            operation="read",
            workspace_root=str(tmp_path)
        )
        assert decision.behavior == PermissionBehavior.DENY


class TestRealWorldScenarios:
    """Test real-world filesystem scenarios."""

    def test_read_python_file(self, tmp_path):
        """Reading Python files should work."""
        file_path = tmp_path / "script.py"
        file_path.write_text("print('hello')")

        decision = validate_filesystem_operation(
            str(file_path),
            operation="read",
            workspace_root=str(tmp_path)
        )
        assert decision.behavior == PermissionBehavior.ALLOW

    def test_write_config_without_secrets(self, tmp_path):
        """Writing config without secrets should work."""
        file_path = tmp_path / "config.json"
        content = '{"debug": true, "port": 8000}'

        decision = validate_filesystem_operation(
            str(file_path),
            operation="write",
            content=content,
            workspace_root=str(tmp_path)
        )
        assert decision.behavior == PermissionBehavior.ALLOW

    def test_edit_file_with_toctou(self, tmp_path):
        """Editing file with TOCTOU protection should work."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("original")

        # Record mtime
        record_file_mtime(str(file_path))

        # Edit (should pass if not modified)
        decision = validate_file_mtime(str(file_path))
        assert decision.behavior == PermissionBehavior.PASSTHROUGH

        # Cleanup
        clear_file_mtime(str(file_path))


class TestSecurityBypass:
    """Test attempts to bypass security."""

    def test_symlink_to_dev_zero(self, tmp_path):
        """Symlink to /dev/zero should be detected."""
        try:
            link = tmp_path / "zero_link"
            link.symlink_to("/dev/zero")

            # Device file check should catch this
            decision = validate_device_file(str(link))
            # Note: This checks the link path, not the target
            # The symlink validator would catch the target

            decision = validate_symlink(str(link))
            # Should detect sensitive path
            assert decision.behavior in [PermissionBehavior.ASK, PermissionBehavior.DENY]
        except (OSError, PermissionError):
            pytest.skip("Cannot create symlink to /dev/zero")

    def test_path_traversal_with_normalization(self):
        """Path traversal with normalization should be detected."""
        # Even after normalization, ../ in parts should be detected
        decision = validate_path_traversal_filesystem("/home/user/../../../etc/passwd")
        assert decision.behavior == PermissionBehavior.ASK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
