"""Backward compatibility tests for tools v1 and v2.

Tests that v1 tools still work, v2 tools accept v1 parameters,
and migration helpers work correctly.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.compatibility import (
    migrate_read_file_params,
    migrate_write_file_params,
    migrate_edit_file_params,
    migrate_glob_params,
    migrate_grep_params,
    migrate_shell_params,
)
from mindflow_backend.agents.tools.filesystem.file_operations_v2 import (
    FileReadToolV2,
    FileWriteToolV2,
    FileEditToolV2,
)
from mindflow_backend.agents.tools.filesystem.search_tools_v2 import (
    GlobToolV2,
    GrepToolV2,
)
from mindflow_backend.agents.tools.system.shell_executor_v2 import (
    ShellExecutorToolV2,
)


class TestV1ParametersInV2Tools:
    """Test that v2 tools accept v1 parameters."""

    @pytest.fixture
    def test_file(self, tmp_path):
        """Create test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Original content\nLine 2\nLine 3")
        return file_path

    def test_read_file_v1_params(self, test_file):
        """Test FileReadToolV2 with v1 parameters."""
        tool = FileReadToolV2()

        # v1 parameters (minimal)
        v1_params = {"file_path": str(test_file)}

        # Migrate to v2
        v2_params = migrate_read_file_params(v1_params)

        # Execute with v2 params
        result = asyncio.run(tool.execute(**v2_params))

        assert result["success"] is True
        assert "Original content" in result["content"]

    def test_write_file_v1_params(self, tmp_path):
        """Test FileWriteToolV2 with v1 parameters."""
        tool = FileWriteToolV2()
        file_path = tmp_path / "new.txt"

        # v1 parameters (minimal)
        v1_params = {
            "file_path": str(file_path),
            "content": "New content"
        }

        # Migrate to v2
        v2_params = migrate_write_file_params(v1_params)

        # Execute with v2 params
        result = asyncio.run(tool.execute(**v2_params))

        assert result["success"] is True
        assert file_path.read_text() == "New content"

    def test_edit_file_v1_params(self, test_file):
        """Test FileEditToolV2 with v1 parameters."""
        tool = FileEditToolV2()

        # v1 parameters (minimal)
        v1_params = {
            "file_path": str(test_file),
            "old_string": "Original",
            "new_string": "Modified"
        }

        # Migrate to v2
        v2_params = migrate_edit_file_params(v1_params)

        # Execute with v2 params
        result = asyncio.run(tool.execute(**v2_params))

        assert result["success"] is True
        assert "Modified content" in test_file.read_text()

    def test_glob_v1_params(self, tmp_path):
        """Test GlobToolV2 with v1 parameters."""
        # Create test files
        (tmp_path / "file1.py").touch()
        (tmp_path / "file2.py").touch()
        (tmp_path / "file3.txt").touch()

        tool = GlobToolV2()

        # v1 parameters
        v1_params = {
            "pattern": "*.py",
            "path": str(tmp_path)
        }

        # Migrate to v2
        v2_params = migrate_glob_params(v1_params)

        # Execute with v2 params
        result = asyncio.run(tool.execute(**v2_params))

        assert result["success"] is True
        assert len(result["matches"]) == 2

    def test_grep_v1_params(self, tmp_path):
        """Test GrepToolV2 with v1 parameters."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def function():\n    return 42\n")

        tool = GrepToolV2()

        # v1 parameters
        v1_params = {
            "pattern": "function",
            "path": str(tmp_path)
        }

        # Migrate to v2
        v2_params = migrate_grep_params(v1_params)

        # Execute with v2 params
        result = asyncio.run(tool.execute(**v2_params))

        assert result["success"] is True

    def test_shell_v1_params(self):
        """Test ShellExecutorToolV2 with v1 parameters."""
        tool = ShellExecutorToolV2()

        # v1 parameters
        v1_params = {"command": "echo 'test'"}

        # Migrate to v2
        v2_params = migrate_shell_params(v1_params)

        # Execute with v2 params
        result = asyncio.run(tool.execute(**v2_params))

        assert result["success"] is True
        assert "test" in result["output"]


class TestParameterMigration:
    """Test parameter migration helpers."""

    def test_read_file_migration_preserves_all_params(self):
        """Test that read file migration preserves all v1 parameters."""
        v1_params = {
            "file_path": "/test/file.txt",
            "offset": 10,
            "limit": 50,
            "encoding": "utf-8"
        }

        v2_params = migrate_read_file_params(v1_params)

        # All v1 params should be preserved
        assert v2_params["file_path"] == v1_params["file_path"]
        assert v2_params["offset"] == v1_params["offset"]
        assert v2_params["limit"] == v1_params["limit"]
        assert v2_params["encoding"] == v1_params["encoding"]

        # v2 defaults should be added
        assert "include_line_numbers" in v2_params

    def test_write_file_migration_adds_v2_defaults(self):
        """Test that write file migration adds v2 defaults."""
        v1_params = {
            "file_path": "/test/file.txt",
            "content": "data"
        }

        v2_params = migrate_write_file_params(v1_params)

        # v2 defaults should be added
        assert v2_params["atomic"] is True
        assert v2_params["backup"] is False
        assert v2_params["preserve_permissions"] is True
        assert v2_params["check_secrets"] is True

    def test_edit_file_migration_adds_v2_features(self):
        """Test that edit file migration adds v2 features."""
        v1_params = {
            "file_path": "/test/file.txt",
            "old_string": "old",
            "new_string": "new"
        }

        v2_params = migrate_edit_file_params(v1_params)

        # v2 features should be added
        assert v2_params["fuzzy_match"] is False
        assert v2_params["fuzzy_threshold"] == 0.8
        assert v2_params["preserve_quotes"] is True
        assert v2_params["dry_run"] is False

    def test_glob_migration_adds_v2_filters(self):
        """Test that glob migration adds v2 filters."""
        v1_params = {
            "pattern": "*.py",
            "path": "/workspace"
        }

        v2_params = migrate_glob_params(v1_params)

        # v2 filters should be added
        assert v2_params["exclude_patterns"] == []
        assert v2_params["max_depth"] is None
        assert v2_params["sort_by_mtime"] is False

    def test_grep_migration_adds_v2_options(self):
        """Test that grep migration adds v2 options."""
        v1_params = {
            "pattern": "TODO",
            "path": "/workspace"
        }

        v2_params = migrate_grep_params(v1_params)

        # v2 options should be added
        assert v2_params["output_mode"] == "content"
        assert v2_params["context_before"] == 0
        assert v2_params["context_after"] == 0
        assert v2_params["show_line_numbers"] is True

    def test_shell_migration_adds_v2_safety(self):
        """Test that shell migration adds v2 safety features."""
        v1_params = {"command": "echo test"}

        v2_params = migrate_shell_params(v1_params)

        # v2 safety features should be added
        assert v2_params["run_in_background"] is False
        assert v2_params["sandbox_mode"] is None


class TestNoBreakingChanges:
    """Test that v2 tools don't break existing functionality."""

    @pytest.fixture
    def test_file(self, tmp_path):
        """Create test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3")
        return file_path

    def test_read_file_basic_usage_unchanged(self, test_file):
        """Test that basic read file usage is unchanged."""
        tool = FileReadToolV2()

        # Basic v1-style usage
        result = asyncio.run(tool.execute(file_path=str(test_file)))

        assert result["success"] is True
        assert "Line 1" in result["content"]
        assert "Line 2" in result["content"]

    def test_write_file_basic_usage_unchanged(self, tmp_path):
        """Test that basic write file usage is unchanged."""
        tool = FileWriteToolV2()
        file_path = tmp_path / "new.txt"

        # Basic v1-style usage
        result = asyncio.run(tool.execute(
            file_path=str(file_path),
            content="Test content"
        ))

        assert result["success"] is True
        assert file_path.read_text() == "Test content"

    def test_edit_file_basic_usage_unchanged(self, test_file):
        """Test that basic edit file usage is unchanged."""
        tool = FileEditToolV2()

        # Basic v1-style usage
        result = asyncio.run(tool.execute(
            file_path=str(test_file),
            old_string="Line 2",
            new_string="Modified Line 2"
        ))

        assert result["success"] is True
        assert "Modified Line 2" in test_file.read_text()

    def test_glob_basic_usage_unchanged(self, tmp_path):
        """Test that basic glob usage is unchanged."""
        (tmp_path / "file1.py").touch()
        (tmp_path / "file2.py").touch()

        tool = GlobToolV2()

        # Basic v1-style usage
        result = asyncio.run(tool.execute(
            pattern="*.py",
            path=str(tmp_path)
        ))

        assert result["success"] is True
        assert len(result["matches"]) == 2

    def test_grep_basic_usage_unchanged(self, tmp_path):
        """Test that basic grep usage is unchanged."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def function():\n    pass\n")

        tool = GrepToolV2()

        # Basic v1-style usage
        result = asyncio.run(tool.execute(
            pattern="function",
            path=str(tmp_path)
        ))

        assert result["success"] is True

    def test_shell_basic_usage_unchanged(self):
        """Test that basic shell usage is unchanged."""
        tool = ShellExecutorToolV2()

        # Basic v1-style usage
        result = asyncio.run(tool.execute(command="echo 'test'"))

        assert result["success"] is True
        assert "test" in result["output"]


class TestV2EnhancementsOptional:
    """Test that v2 enhancements are optional."""

    @pytest.fixture
    def test_file(self, tmp_path):
        """Create test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Content")
        return file_path

    def test_read_file_line_numbers_optional(self, test_file):
        """Test that line numbers are optional."""
        tool = FileReadToolV2()

        # Without line numbers (v1 style)
        result1 = asyncio.run(tool.execute(
            file_path=str(test_file),
            include_line_numbers=False
        ))

        # With line numbers (v2 feature)
        result2 = asyncio.run(tool.execute(
            file_path=str(test_file),
            include_line_numbers=True
        ))

        assert result1["success"] is True
        assert result2["success"] is True

    def test_write_file_atomic_optional(self, tmp_path):
        """Test that atomic writes are optional."""
        tool = FileWriteToolV2()

        # Non-atomic (v1 style)
        file1 = tmp_path / "file1.txt"
        result1 = asyncio.run(tool.execute(
            file_path=str(file1),
            content="data",
            atomic=False
        ))

        # Atomic (v2 feature)
        file2 = tmp_path / "file2.txt"
        result2 = asyncio.run(tool.execute(
            file_path=str(file2),
            content="data",
            atomic=True
        ))

        assert result1["success"] is True
        assert result2["success"] is True

    def test_edit_file_fuzzy_match_optional(self, test_file):
        """Test that fuzzy match is optional."""
        tool = FileEditToolV2()

        # Exact match (v1 style)
        result1 = asyncio.run(tool.execute(
            file_path=str(test_file),
            old_string="Content",
            new_string="New Content",
            fuzzy_match=False
        ))

        assert result1["success"] is True

    def test_glob_exclude_patterns_optional(self, tmp_path):
        """Test that exclude patterns are optional."""
        (tmp_path / "file1.py").touch()
        (tmp_path / "test_file.py").touch()

        tool = GlobToolV2()

        # Without exclude (v1 style)
        result1 = asyncio.run(tool.execute(
            pattern="*.py",
            path=str(tmp_path)
        ))

        # With exclude (v2 feature)
        result2 = asyncio.run(tool.execute(
            pattern="*.py",
            path=str(tmp_path),
            exclude_patterns=["test_*"]
        ))

        assert result1["success"] is True
        assert len(result1["matches"]) == 2

        assert result2["success"] is True
        assert len(result2["matches"]) == 1

    def test_grep_context_lines_optional(self, tmp_path):
        """Test that context lines are optional."""
        test_file = tmp_path / "test.py"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        tool = GrepToolV2()

        # Without context (v1 style)
        result1 = asyncio.run(tool.execute(
            pattern="Line 2",
            path=str(tmp_path),
            output_mode="content"
        ))

        # With context (v2 feature)
        result2 = asyncio.run(tool.execute(
            pattern="Line 2",
            path=str(tmp_path),
            output_mode="content",
            context_before=1,
            context_after=1
        ))

        assert result1["success"] is True
        assert result2["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
