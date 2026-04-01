"""Unit tests for backward compatibility module.

Tests parameter migration helpers, deprecation warnings, and migration guide.
"""

from __future__ import annotations

import warnings

import pytest

from mindflow_backend.agents.tools.compatibility import (
    MIGRATION_GUIDE,
    migrate_edit_file_params,
    migrate_glob_params,
    migrate_grep_params,
    migrate_read_file_params,
    migrate_shell_params,
    migrate_write_file_params,
    print_migration_guide,
)


class TestReadFileMigration:
    """Test read file parameter migration."""

    def test_migrate_minimal_params(self):
        """Test migrating minimal v1 parameters."""
        v1_params = {"file_path": "test.txt"}
        v2_params = migrate_read_file_params(v1_params)

        assert v2_params["file_path"] == "test.txt"
        assert v2_params["include_line_numbers"] is True
        assert v2_params["encoding"] == "utf-8"

    def test_migrate_preserves_existing_params(self):
        """Test that existing parameters are preserved."""
        v1_params = {
            "file_path": "test.txt",
            "offset": 10,
            "limit": 50
        }
        v2_params = migrate_read_file_params(v1_params)

        assert v2_params["file_path"] == "test.txt"
        assert v2_params["offset"] == 10
        assert v2_params["limit"] == 50
        assert v2_params["include_line_numbers"] is True

    def test_migrate_does_not_override_explicit_values(self):
        """Test that explicit values are not overridden."""
        v1_params = {
            "file_path": "test.txt",
            "include_line_numbers": False,
            "encoding": "latin-1"
        }
        v2_params = migrate_read_file_params(v1_params)

        assert v2_params["include_line_numbers"] is False
        assert v2_params["encoding"] == "latin-1"


class TestWriteFileMigration:
    """Test write file parameter migration."""

    def test_migrate_minimal_params(self):
        """Test migrating minimal v1 parameters."""
        v1_params = {
            "file_path": "test.txt",
            "content": "data"
        }
        v2_params = migrate_write_file_params(v1_params)

        assert v2_params["file_path"] == "test.txt"
        assert v2_params["content"] == "data"
        assert v2_params["atomic"] is True
        assert v2_params["backup"] is False
        assert v2_params["preserve_permissions"] is True
        assert v2_params["check_secrets"] is True
        assert v2_params["generate_git_diff"] is False

    def test_migrate_preserves_existing_params(self):
        """Test that existing parameters are preserved."""
        v1_params = {
            "file_path": "test.txt",
            "content": "data",
            "encoding": "utf-16"
        }
        v2_params = migrate_write_file_params(v1_params)

        assert v2_params["encoding"] == "utf-16"
        assert v2_params["atomic"] is True


class TestEditFileMigration:
    """Test edit file parameter migration."""

    def test_migrate_minimal_params(self):
        """Test migrating minimal v1 parameters."""
        v1_params = {
            "file_path": "test.txt",
            "old_string": "old",
            "new_string": "new"
        }
        v2_params = migrate_edit_file_params(v1_params)

        assert v2_params["file_path"] == "test.txt"
        assert v2_params["old_string"] == "old"
        assert v2_params["new_string"] == "new"
        assert v2_params["replace_all"] is False
        assert v2_params["fuzzy_match"] is False
        assert v2_params["fuzzy_threshold"] == 0.8
        assert v2_params["preserve_quotes"] is True
        assert v2_params["dry_run"] is False
        assert v2_params["check_secrets"] is True
        assert v2_params["generate_git_diff"] is False

    def test_migrate_with_replace_all(self):
        """Test migration with replace_all flag."""
        v1_params = {
            "file_path": "test.txt",
            "old_string": "old",
            "new_string": "new",
            "replace_all": True
        }
        v2_params = migrate_edit_file_params(v1_params)

        assert v2_params["replace_all"] is True


class TestGlobMigration:
    """Test glob parameter migration."""

    def test_migrate_minimal_params(self):
        """Test migrating minimal v1 parameters."""
        v1_params = {
            "pattern": "*.py",
            "path": "/workspace"
        }
        v2_params = migrate_glob_params(v1_params)

        assert v2_params["pattern"] == "*.py"
        assert v2_params["path"] == "/workspace"
        assert v2_params["exclude_patterns"] == []
        assert v2_params["max_depth"] is None
        assert v2_params["sort_by_mtime"] is False
        assert v2_params["case_sensitive"] is True
        assert v2_params["head_limit"] is None
        assert v2_params["offset"] == 0

    def test_migrate_with_exclude_patterns(self):
        """Test migration with exclude patterns."""
        v1_params = {
            "pattern": "*.py",
            "path": "/workspace",
            "exclude_patterns": ["test_*.py"]
        }
        v2_params = migrate_glob_params(v1_params)

        assert v2_params["exclude_patterns"] == ["test_*.py"]


class TestGrepMigration:
    """Test grep parameter migration."""

    def test_migrate_minimal_params(self):
        """Test migrating minimal v1 parameters."""
        v1_params = {
            "pattern": "TODO",
            "path": "/workspace"
        }
        v2_params = migrate_grep_params(v1_params)

        assert v2_params["pattern"] == "TODO"
        assert v2_params["path"] == "/workspace"
        assert v2_params["glob_pattern"] is None
        assert v2_params["output_mode"] == "content"
        assert v2_params["context_before"] == 0
        assert v2_params["context_after"] == 0
        assert v2_params["show_line_numbers"] is True
        assert v2_params["case_sensitive"] is True
        assert v2_params["multiline"] is False
        assert v2_params["head_limit"] is None
        assert v2_params["offset"] == 0

    def test_migrate_with_context_lines(self):
        """Test migration with context lines."""
        v1_params = {
            "pattern": "TODO",
            "path": "/workspace",
            "context_before": 2,
            "context_after": 2
        }
        v2_params = migrate_grep_params(v1_params)

        assert v2_params["context_before"] == 2
        assert v2_params["context_after"] == 2


class TestShellMigration:
    """Test shell parameter migration."""

    def test_migrate_minimal_params(self):
        """Test migrating minimal v1 parameters."""
        v1_params = {"command": "echo test"}
        v2_params = migrate_shell_params(v1_params)

        assert v2_params["command"] == "echo test"
        assert v2_params["run_in_background"] is False
        assert v2_params["sandbox_mode"] is None

    def test_migrate_with_timeout(self):
        """Test migration with timeout."""
        v1_params = {
            "command": "echo test",
            "timeout": 30
        }
        v2_params = migrate_shell_params(v1_params)

        assert v2_params["timeout"] == 30
        assert v2_params["run_in_background"] is False


class TestMigrationGuide:
    """Test migration guide."""

    def test_migration_guide_exists(self):
        """Test that migration guide exists."""
        assert MIGRATION_GUIDE is not None
        assert len(MIGRATION_GUIDE) > 0

    def test_migration_guide_content(self):
        """Test migration guide contains expected content."""
        assert "Migration Guide" in MIGRATION_GUIDE
        assert "v2.0.0" in MIGRATION_GUIDE
        assert "Breaking Changes" in MIGRATION_GUIDE
        assert "FileReadToolV2" in MIGRATION_GUIDE
        assert "FileWriteToolV2" in MIGRATION_GUIDE
        assert "FileEditToolV2" in MIGRATION_GUIDE
        assert "GlobToolV2" in MIGRATION_GUIDE
        assert "GrepToolV2" in MIGRATION_GUIDE
        assert "ShellExecutorToolV2" in MIGRATION_GUIDE

    def test_migration_guide_has_timeline(self):
        """Test migration guide includes deprecation timeline."""
        assert "v3.0.0" in MIGRATION_GUIDE
        assert "Timeline" in MIGRATION_GUIDE or "timeline" in MIGRATION_GUIDE

    def test_migration_guide_has_examples(self):
        """Test migration guide includes code examples."""
        # Should have import statements
        assert "from mindflow_backend" in MIGRATION_GUIDE or "import" in MIGRATION_GUIDE

    def test_print_migration_guide(self, capsys):
        """Test printing migration guide."""
        print_migration_guide()

        captured = capsys.readouterr()
        assert "Migration Guide" in captured.out


class TestParameterCompatibility:
    """Test that v1 parameters work in v2 format."""

    def test_all_v1_params_preserved_in_v2(self):
        """Test that all v1 parameters are preserved in v2."""
        # Read file
        v1_read = {"file_path": "test.txt", "offset": 10}
        v2_read = migrate_read_file_params(v1_read)
        assert all(k in v2_read for k in v1_read.keys())

        # Write file
        v1_write = {"file_path": "test.txt", "content": "data"}
        v2_write = migrate_write_file_params(v1_write)
        assert all(k in v2_write for k in v1_write.keys())

        # Edit file
        v1_edit = {"file_path": "test.txt", "old_string": "old", "new_string": "new"}
        v2_edit = migrate_edit_file_params(v1_edit)
        assert all(k in v2_edit for k in v1_edit.keys())

        # Glob
        v1_glob = {"pattern": "*.py", "path": "/workspace"}
        v2_glob = migrate_glob_params(v1_glob)
        assert all(k in v2_glob for k in v1_glob.keys())

        # Grep
        v1_grep = {"pattern": "TODO", "path": "/workspace"}
        v2_grep = migrate_grep_params(v1_grep)
        assert all(k in v2_grep for k in v1_grep.keys())

        # Shell
        v1_shell = {"command": "echo test"}
        v2_shell = migrate_shell_params(v1_shell)
        assert all(k in v2_shell for k in v1_shell.keys())

    def test_v2_defaults_are_sensible(self):
        """Test that v2 defaults are sensible."""
        # Read defaults
        v2_read = migrate_read_file_params({"file_path": "test.txt"})
        assert v2_read["include_line_numbers"] is True  # Helpful default
        assert v2_read["encoding"] == "utf-8"  # Standard encoding

        # Write defaults
        v2_write = migrate_write_file_params({"file_path": "test.txt", "content": "data"})
        assert v2_write["atomic"] is True  # Safe default
        assert v2_write["check_secrets"] is True  # Security default

        # Edit defaults
        v2_edit = migrate_edit_file_params({
            "file_path": "test.txt",
            "old_string": "old",
            "new_string": "new"
        })
        assert v2_edit["replace_all"] is False  # Conservative default
        assert v2_edit["dry_run"] is False  # Action default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
