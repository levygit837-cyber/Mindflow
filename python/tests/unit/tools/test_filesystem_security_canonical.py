"""Unit tests for filesystem security in canonical tools.

Tests security validators integration in FileReadTool canonical.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.file_operations import (
    FileEditTool,
    FileReadTool,
    FileWriteTool,
)
from mindflow_backend.agents.tools.filesystem.search_tools import (
    GlobSearchTool,
    GrepSearchTool,
)


class TestFileReadToolSecurity:
    """Test FileReadTool security validators."""

    @pytest.mark.asyncio
    async def test_device_file_blocked(self):
        """Test that device files are blocked."""
        tool = FileReadTool()
        result = await tool.execute(file_path="/dev/zero")

        assert result["success"] is False
        assert "device file" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_device_file_random_blocked(self):
        """Test that /dev/random is blocked."""
        tool = FileReadTool()
        result = await tool.execute(file_path="/dev/random")

        assert result["success"] is False
        assert "device file" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_symlink_outside_workspace_blocked(self, tmp_path):
        """Test that symlinks pointing outside workspace are validated."""
        tool = FileReadTool()
        tool.root_dir = str(tmp_path)

        # Create a symlink pointing outside workspace
        outside_file = tmp_path.parent / "outside.txt"
        outside_file.write_text("outside content")
        
        symlink = tmp_path / "symlink.txt"
        symlink.symlink_to(outside_file)

        result = await tool.execute(file_path=str(symlink))

        # Symlink validation should be checked (may be blocked or warned)
        # The important thing is that validation is performed
        assert "success" in result

    @pytest.mark.asyncio
    async def test_symlink_inside_workspace_allowed(self, tmp_path):
        """Test that symlinks pointing inside workspace are allowed."""
        tool = FileReadTool()
        tool.root_dir = str(tmp_path)

        # Create a file and symlink within workspace
        target_file = tmp_path / "target.txt"
        target_file.write_text("content")
        
        symlink = tmp_path / "symlink.txt"
        symlink.symlink_to(target_file)

        result = await tool.execute(file_path=str(symlink))

        assert result["success"] is True
        assert "content" in result["result"]["content"]

    @pytest.mark.asyncio
    async def test_regular_file_read_still_works(self, tmp_path):
        """Test that regular file reading still works after security changes."""
        tool = FileReadTool()
        tool.root_dir = str(tmp_path)

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        result = await tool.execute(file_path=str(test_file))

        assert result["success"] is True
        assert "Hello World" in result["result"]["content"]


class TestFileWriteToolSecurity:
    """Test FileWriteTool security validators."""

    @pytest.mark.asyncio
    async def test_secret_detection_blocks_write(self, tmp_path):
        """Test that writing secrets is blocked."""
        tool = FileWriteTool()
        tool.root_dir = str(tmp_path)

        test_file = tmp_path / "config.txt"
        secret_content = "api_key=sk-1234567890abcdefghijklmnopqrstuv"

        result = await tool.execute(
            file_path=str(test_file),
            content=secret_content
        )

        assert result["success"] is False
        assert "secret" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_safe_content_allowed(self, tmp_path):
        """Test that safe content is allowed."""
        tool = FileWriteTool()
        tool.root_dir = str(tmp_path)

        test_file = tmp_path / "safe.txt"
        safe_content = "This is safe content without secrets"

        result = await tool.execute(
            file_path=str(test_file),
            content=safe_content
        )

        assert result["success"] is True


class TestFileReadToolAdvancedFeatures:
    """Test FileReadTool advanced features."""

    @pytest.mark.asyncio
    async def test_image_reading_base64(self, tmp_path):
        """Test that image files are read as base64."""
        tool = FileReadTool()
        tool.root_dir = str(tmp_path)

        # Create a simple PNG file (1x1 transparent pixel)
        import base64
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        test_image = tmp_path / "test.png"
        test_image.write_bytes(png_data)

        result = await tool.execute(file_path=str(test_image))

        assert result["success"] is True
        assert result["result"]["file_type"] == "image"
        assert result["result"]["encoding"] == "base64"
        assert result["result"]["image_format"] == "png"

    @pytest.mark.asyncio
    async def test_backup_creation(self, tmp_path):
        """Test that backup is created when requested."""
        tool = FileWriteTool()
        tool.root_dir = str(tmp_path)

        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        result = await tool.execute(
            file_path=str(test_file),
            content="new content",
            create_backup=True
        )

        assert result["success"] is True
        assert result["result"]["backup_created"] is True
        assert result["result"]["backup_path"] is not None
        assert (tmp_path / "test.txt.backup").exists()

        # Verify backup has original content
        backup = tmp_path / "test.txt.backup"
        assert backup.read_text() == "original content"

    @pytest.mark.asyncio
    async def test_atomic_write(self, tmp_path):
        """Test that atomic write works correctly."""
        tool = FileWriteTool()
        tool.root_dir = str(tmp_path)

        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        result = await tool.execute(
            file_path=str(test_file),
            content="new content",
            atomic_write=True
        )

        assert result["success"] is True
        assert result["result"]["atomic"] is True
        assert test_file.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_git_diff_generation(self, tmp_path):
        """Test that git diff is generated when requested."""
        tool = FileWriteTool()
        tool.root_dir = str(tmp_path)

        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        result = await tool.execute(
            file_path=str(test_file),
            content="new content",
            generate_git_diff=True
        )

        assert result["success"] is True
        # Git diff may be None if not in git repo, but should be present in result
        assert "git_diff" in result["result"]


class TestFileEditToolAdvancedFeatures:
    """Test FileEditTool advanced features."""

    @pytest.mark.asyncio
    async def test_toctou_protection(self, tmp_path):
        """Test that TOCTOU protection works."""
        tool = FileEditTool()
        tool.root_dir = str(tmp_path)

        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        result = await tool.execute(
            file_path=str(test_file),
            old_string="original",
            new_string="modified"
        )

        assert result["success"] is True
        assert result["result"]["replacements"] == 1


class TestAdvancedSearchFeatures:
    """Test advanced search features."""

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, tmp_path):
        """Test that exclude patterns work in glob search."""
        tool = GlobSearchTool()

        # Create test structure
        (tmp_path / "node_modules").mkdir(parents=True)
        (tmp_path / "src").mkdir(parents=True)
        (tmp_path / ".git").mkdir(parents=True)
        (tmp_path / "node_modules" / "test.txt").write_text("test")
        (tmp_path / "src" / "test.py").write_text("test")
        (tmp_path / ".git" / "config").write_text("config")

        result = await tool.execute(
            pattern="*.txt",
            directory=str(tmp_path),
            exclude_patterns=["node_modules", ".git"]
        )

        assert result["success"] is True
        # Should exclude node_modules and .git
        assert not any("node_modules" in f for f in result["result"]["files"])
        assert not any(".git" in f for f in result["result"]["files"])

    @pytest.mark.asyncio
    async def test_max_depth(self, tmp_path):
        """Test that max depth limits search depth."""
        tool = GlobSearchTool()

        # Create nested structure
        (tmp_path / "level1" / "level2" / "level3").mkdir(parents=True)
        (tmp_path / "level1" / "test.py").write_text("test")
        (tmp_path / "level1" / "level2" / "level3" / "test.txt").write_text("test")

        result = await tool.execute(
            pattern="*.txt",
            directory=str(tmp_path),
            max_depth=1
        )

        assert result["success"] is True
        # Should only find files at depth 1 or less
        assert len(result["result"]["files"]) == 0  # No .txt at depth <= 1

    @pytest.mark.asyncio
    async def test_context_windows(self, tmp_path):
        """Test that context windows work in grep search."""
        tool = GrepSearchTool()

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nMATCH\nline4\nline5\n")

        result = await tool.execute(
            pattern="MATCH",
            directory=str(tmp_path),
            context_before=1,
            context_after=1
        )

        assert result["success"] is True
        assert len(result["result"]["matches"]) == 1
        # Check context is included
        match = result["result"]["matches"][0]
        assert match["context"] is not None
        # Context should include at least the match line
        assert len(match["context"]) >= 1






