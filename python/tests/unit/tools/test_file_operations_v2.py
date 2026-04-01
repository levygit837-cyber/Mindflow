"""Unit tests for file operations tools v2.

Tests FileReadTool, FileWriteTool, and FileEditTool v2 with full
integration of schemas, validators, and security features.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.file_operations_v2 import (
    FileEditToolV2,
    FileReadToolV2,
    FileWriteToolV2,
)


class TestFileReadToolV2:
    """Test FileReadTool v2."""

    @pytest.mark.asyncio
    async def test_read_simple_file(self, tmp_path):
        """Test reading a simple text file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello\nWorld\n")

        tool = FileReadToolV2(root_dir=str(tmp_path))
        result = await tool.execute(file_path=str(test_file))

        assert result["success"] is True
        assert "Hello\nWorld\n" in result["content"]
        assert result["total_lines"] == 2

    @pytest.mark.asyncio
    async def test_read_with_line_numbers(self, tmp_path):
        """Test reading with line numbers."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        tool = FileReadToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            include_line_numbers=True
        )

        assert result["success"] is True
        assert "1\tLine 1" in result["content"]
        assert "2\tLine 2" in result["content"]

    @pytest.mark.asyncio
    async def test_read_with_pagination(self, tmp_path):
        """Test reading with offset and limit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("\n".join([f"Line {i}" for i in range(1, 11)]))

        tool = FileReadToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            offset=2,
            limit=3
        )

        assert result["success"] is True
        assert result["lines_returned"] == 3
        assert result["offset"] == 2
        assert "Line 3" in result["content"]

    @pytest.mark.asyncio
    async def test_read_device_file_blocked(self):
        """Test that device files are blocked."""
        tool = FileReadToolV2()
        result = await tool.execute(file_path="/dev/zero")

        assert result["success"] is False
        assert result["error_code"] == "DEVICE_FILE_BLOCKED"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tmp_path):
        """Test reading nonexistent file."""
        tool = FileReadToolV2(root_dir=str(tmp_path))
        result = await tool.execute(file_path=str(tmp_path / "nonexistent.txt"))

        assert result["success"] is False
        assert result["error_code"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_read_image_returns_base64(self, tmp_path):
        """Test reading image file returns base64."""
        # Create a fake PNG file
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake image data")

        tool = FileReadToolV2(root_dir=str(tmp_path))
        result = await tool.execute(file_path=str(test_file))

        assert result["success"] is True
        assert result["file_type"] == "image"
        assert result["encoding"] == "base64"
        assert "content" in result


class TestFileWriteToolV2:
    """Test FileWriteTool v2."""

    @pytest.mark.asyncio
    async def test_write_new_file(self, tmp_path):
        """Test writing a new file."""
        test_file = tmp_path / "new.txt"

        tool = FileWriteToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            content="Hello World"
        )

        assert result["success"] is True
        assert result["file_existed"] is False
        assert test_file.read_text() == "Hello World"

    @pytest.mark.asyncio
    async def test_write_with_backup(self, tmp_path):
        """Test writing with backup creation."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("Original content")

        tool = FileWriteToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            content="New content",
            backup=True
        )

        assert result["success"] is True
        assert result["backup_created"] is True
        assert Path(result["backup_path"]).exists()
        assert Path(result["backup_path"]).read_text() == "Original content"
        assert test_file.read_text() == "New content"

    @pytest.mark.asyncio
    async def test_write_atomic(self, tmp_path):
        """Test atomic write."""
        test_file = tmp_path / "atomic.txt"

        tool = FileWriteToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            content="Atomic content",
            atomic=True
        )

        assert result["success"] is True
        assert result["atomic"] is True
        assert test_file.read_text() == "Atomic content"

    @pytest.mark.asyncio
    async def test_write_with_secrets_blocked(self, tmp_path):
        """Test that secrets are detected and blocked."""
        test_file = tmp_path / "secrets.txt"

        tool = FileWriteToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            content="API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890abcdefgh",
            check_secrets=True
        )

        assert result["success"] is False
        assert result["error_code"] == "SECRETS_DETECTED"

    @pytest.mark.asyncio
    async def test_write_metadata_tracking(self, tmp_path):
        """Test that metadata is tracked."""
        test_file = tmp_path / "metadata.txt"

        tool = FileWriteToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            content="Content with metadata"
        )

        assert result["success"] is True
        assert "metadata" in result
        assert result["metadata"]["file_path"] == str(test_file)
        assert result["metadata"]["modification_time_after"] is not None


class TestFileEditToolV2:
    """Test FileEditTool v2."""

    @pytest.mark.asyncio
    async def test_edit_simple_replace(self, tmp_path):
        """Test simple string replacement."""
        test_file = tmp_path / "edit.txt"
        test_file.write_text("Hello World\nGoodbye World\n")

        tool = FileEditToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            old_string="World",
            new_string="Universe"
        )

        assert result["success"] is True
        assert result["replacements"] == 1
        assert "Hello Universe" in test_file.read_text()

    @pytest.mark.asyncio
    async def test_edit_replace_all(self, tmp_path):
        """Test replace all occurrences."""
        test_file = tmp_path / "edit.txt"
        test_file.write_text("foo bar foo baz foo")

        tool = FileEditToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            old_string="foo",
            new_string="qux",
            replace_all=True
        )

        assert result["success"] is True
        assert result["replacements"] == 3
        assert test_file.read_text() == "qux bar qux baz qux"

    @pytest.mark.asyncio
    async def test_edit_string_not_found(self, tmp_path):
        """Test editing when string not found."""
        test_file = tmp_path / "edit.txt"
        test_file.write_text("Hello World")

        tool = FileEditToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            old_string="Nonexistent",
            new_string="Something"
        )

        assert result["success"] is False
        assert result["error_code"] == "STRING_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_edit_multiple_matches_error(self, tmp_path):
        """Test that multiple matches without replace_all fails."""
        test_file = tmp_path / "edit.txt"
        test_file.write_text("foo foo foo")

        tool = FileEditToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            old_string="foo",
            new_string="bar",
            replace_all=False
        )

        assert result["success"] is False
        assert result["error_code"] == "MULTIPLE_MATCHES"
        assert result["match_count"] == 3

    @pytest.mark.asyncio
    async def test_edit_dry_run(self, tmp_path):
        """Test dry run mode."""
        test_file = tmp_path / "edit.txt"
        original_content = "Hello World"
        test_file.write_text(original_content)

        tool = FileEditToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            old_string="World",
            new_string="Universe",
            dry_run=True
        )

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "preview" in result
        # File should not be modified
        assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_edit_with_secrets_blocked(self, tmp_path):
        """Test that edits introducing secrets are blocked."""
        test_file = tmp_path / "edit.txt"
        test_file.write_text("API_KEY=placeholder")

        tool = FileEditToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(test_file),
            old_string="placeholder",
            new_string="sk-proj-abcdefghijklmnopqrstuvwxyz1234567890abcdefgh",
            check_secrets=True
        )

        assert result["success"] is False
        assert result["error_code"] == "SECRETS_DETECTED"

    @pytest.mark.asyncio
    async def test_edit_nonexistent_file(self, tmp_path):
        """Test editing nonexistent file."""
        tool = FileEditToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            file_path=str(tmp_path / "nonexistent.txt"),
            old_string="foo",
            new_string="bar"
        )

        assert result["success"] is False
        assert result["error_code"] == "FILE_NOT_FOUND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
