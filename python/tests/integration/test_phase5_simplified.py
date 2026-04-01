"""Simplified tests for Phase 5 modules - direct imports without full MindFlow chain.

Tests individual Phase 5 modules to validate implementation without
triggering circular imports in the existing codebase.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


class TestGitIntegration:
    """Test git integration module."""

    @pytest.mark.asyncio
    async def test_git_diff_not_a_repo(self, tmp_path):
        """Test git diff on non-repository."""
        from mindflow_backend.agents.tools.integrations.git_integration import (
            fetch_single_file_git_diff
        )

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = await fetch_single_file_git_diff(str(test_file), str(tmp_path))

        assert result["success"] is False
        assert "not a git repository" in result["error"].lower()

    def test_git_diff_sync_not_a_repo(self, tmp_path):
        """Test sync git diff on non-repository."""
        from mindflow_backend.agents.tools.integrations.git_integration import (
            fetch_single_file_git_diff_sync
        )

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = fetch_single_file_git_diff_sync(str(test_file), str(tmp_path))

        assert result["success"] is False
        assert "not a git repository" in result["error"].lower()

    def test_git_operation_tracker(self):
        """Test git operation tracking."""
        from mindflow_backend.agents.tools.integrations.git_integration import (
            track_git_operation,
            get_git_operations,
            clear_git_operations
        )

        clear_git_operations()

        track_git_operation("edit", "/test/file.py", {"user": "test"})
        track_git_operation("write", "/test/file2.py", {"user": "test"})

        operations = get_git_operations()

        assert len(operations) == 2
        assert operations[0]["type"] == "edit"
        assert operations[1]["type"] == "write"

    def test_diff_formatting(self):
        """Test diff formatting utilities."""
        from mindflow_backend.agents.tools.integrations.git_integration import (
            format_diff_for_display,
            parse_diff_stats
        )

        diff = "\n".join([f"+ Line {i}" for i in range(100)])

        formatted = format_diff_for_display(diff, max_lines=10)
        assert "..." in formatted
        assert "90 more lines" in formatted

        stats = parse_diff_stats(diff)
        assert stats["additions"] == 100
        assert stats["deletions"] == 0


class TestFileHistory:
    """Test file history module."""

    def test_create_snapshot(self, tmp_path):
        """Test snapshot creation."""
        from mindflow_backend.agents.tools.integrations.file_history import (
            FileHistoryStore
        )

        test_file = tmp_path / "test.txt"
        test_file.write_text("Original content")

        store = FileHistoryStore(history_dir=str(tmp_path / "history"))
        result = store.create_snapshot(
            str(test_file),
            "edit",
            {"user": "test"}
        )

        assert result["success"] is True
        assert "snapshot_id" in result
        assert Path(result["snapshot_path"]).exists()

    def test_list_snapshots(self, tmp_path):
        """Test listing snapshots."""
        from mindflow_backend.agents.tools.integrations.file_history import (
            FileHistoryStore
        )

        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        store = FileHistoryStore(history_dir=str(tmp_path / "history"))

        # Create multiple snapshots
        store.create_snapshot(str(test_file), "edit1")
        store.create_snapshot(str(test_file), "edit2")

        snapshots = store.list_snapshots(str(test_file))

        assert len(snapshots) == 2
        assert snapshots[0]["operation"] == "edit2"  # Newest first

    def test_restore_snapshot(self, tmp_path):
        """Test snapshot restoration."""
        from mindflow_backend.agents.tools.integrations.file_history import (
            FileHistoryStore
        )

        test_file = tmp_path / "test.txt"
        original_content = "Original content"
        test_file.write_text(original_content)

        store = FileHistoryStore(history_dir=str(tmp_path / "history"))

        # Create snapshot
        snapshot = store.create_snapshot(str(test_file), "edit")
        snapshot_id = snapshot["snapshot_id"]

        # Modify file
        test_file.write_text("Modified content")

        # Restore
        result = store.restore_snapshot(snapshot_id)

        assert result["success"] is True
        assert test_file.read_text() == original_content


class TestAnalytics:
    """Test analytics module."""

    def test_metrics_collector(self):
        """Test metrics collection."""
        from mindflow_backend.agents.tools.analytics.tool_metrics import (
            ToolMetricsCollector
        )

        collector = ToolMetricsCollector()

        # Start operation
        op_id = collector.start_operation("test_tool", "test_op")

        # End operation
        metric = collector.end_operation(op_id, success=True)

        assert metric is not None
        assert metric.success is True
        assert metric.duration is not None

        # Get stats
        stats = collector.get_stats("test_tool")
        assert stats["total_executions"] == 1
        assert stats["success_rate"] == 100.0

    def test_track_operation_context_manager(self):
        """Test track_operation context manager."""
        from mindflow_backend.agents.tools.analytics.tool_metrics import (
            track_operation,
            get_metrics_collector
        )

        collector = get_metrics_collector()
        collector.clear_metrics()

        with track_operation("test_tool", "test_op", {"key": "value"}):
            pass  # Simulated operation

        stats = collector.get_stats("test_tool")
        assert stats["total_executions"] >= 1

    def test_metrics_summary(self):
        """Test metrics summary."""
        from mindflow_backend.agents.tools.analytics.tool_metrics import (
            ToolMetricsCollector
        )

        collector = ToolMetricsCollector()
        collector.clear_metrics()

        # Create some operations
        for i in range(5):
            op_id = collector.start_operation("tool1", "op")
            collector.end_operation(op_id, success=True)

        for i in range(3):
            op_id = collector.start_operation("tool2", "op")
            collector.end_operation(op_id, success=i < 2)  # 2 success, 1 fail

        summary = collector.get_summary()

        assert summary["total_tools"] == 2
        assert summary["total_executions"] == 8
        assert summary["successful_executions"] == 7
        assert summary["failed_executions"] == 1


class TestCaching:
    """Test caching module."""

    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        from mindflow_backend.agents.tools.caching.result_cache import ResultCache

        cache = ResultCache(max_size=10, max_memory_mb=1)

        # Set and get
        cache.set("key1", {"data": "value1"})
        value = cache.get("key1")

        assert value is not None
        assert value["data"] == "value1"

    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        import time
        from mindflow_backend.agents.tools.caching.result_cache import ResultCache

        cache = ResultCache(default_ttl=0.1)  # 100ms TTL

        cache.set("key1", {"data": "value1"})

        # Should exist immediately
        assert cache.get("key1") is not None

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired
        assert cache.get("key1") is None

    def test_cache_lru_eviction(self):
        """Test LRU eviction."""
        from mindflow_backend.agents.tools.caching.result_cache import ResultCache

        cache = ResultCache(max_size=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add new entry - should evict key2 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") is not None  # Still there
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") is not None  # Still there
        assert cache.get("key4") is not None  # New entry

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        from mindflow_backend.agents.tools.caching.result_cache import ResultCache

        cache = ResultCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("prefix_key3", "value3")

        # Invalidate single key
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None

        # Invalidate by pattern
        count = cache.invalidate_pattern("prefix_")
        assert count == 1
        assert cache.get("prefix_key3") is None

    def test_cache_stats(self):
        """Test cache statistics."""
        from mindflow_backend.agents.tools.caching.result_cache import ResultCache

        cache = ResultCache(max_size=100, max_memory_mb=10)

        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        stats = cache.get_stats()

        assert stats["entries"] == 2
        assert stats["max_size"] == 100
        assert stats["total_size_bytes"] > 0


class TestCompatibility:
    """Test backward compatibility module."""

    def test_parameter_migration_read(self):
        """Test read file parameter migration."""
        from mindflow_backend.agents.tools.compatibility import (
            migrate_read_file_params
        )

        v1_params = {"file_path": "test.txt"}
        v2_params = migrate_read_file_params(v1_params)

        assert v2_params["file_path"] == "test.txt"
        assert v2_params["include_line_numbers"] is True
        assert v2_params["encoding"] == "utf-8"

    def test_parameter_migration_write(self):
        """Test write file parameter migration."""
        from mindflow_backend.agents.tools.compatibility import (
            migrate_write_file_params
        )

        v1_params = {"file_path": "test.txt", "content": "data"}
        v2_params = migrate_write_file_params(v1_params)

        assert v2_params["atomic"] is True
        assert v2_params["backup"] is False
        assert v2_params["check_secrets"] is True

    def test_parameter_migration_edit(self):
        """Test edit file parameter migration."""
        from mindflow_backend.agents.tools.compatibility import (
            migrate_edit_file_params
        )

        v1_params = {
            "file_path": "test.txt",
            "old_string": "old",
            "new_string": "new"
        }
        v2_params = migrate_edit_file_params(v1_params)

        assert v2_params["replace_all"] is False
        assert v2_params["dry_run"] is False
        assert v2_params["preserve_quotes"] is True

    def test_migration_guide_available(self):
        """Test that migration guide is available."""
        from mindflow_backend.agents.tools.compatibility import MIGRATION_GUIDE

        assert "Migration Guide" in MIGRATION_GUIDE
        assert "v2.0.0" in MIGRATION_GUIDE
        assert "Breaking Changes" in MIGRATION_GUIDE


class TestToolsV2DirectImport:
    """Test tools v2 can be imported directly."""

    def test_import_file_operations_v2(self):
        """Test importing file operations v2."""
        from mindflow_backend.agents.tools.filesystem.file_operations_v2 import (
            FileReadToolV2,
            FileWriteToolV2,
            FileEditToolV2
        )

        assert FileReadToolV2 is not None
        assert FileWriteToolV2 is not None
        assert FileEditToolV2 is not None

    def test_import_search_tools_v2(self):
        """Test importing search tools v2."""
        from mindflow_backend.agents.tools.filesystem.search_tools_v2 import (
            GlobToolV2,
            GrepToolV2
        )

        assert GlobToolV2 is not None
        assert GrepToolV2 is not None

    def test_import_shell_executor_v2(self):
        """Test importing shell executor v2."""
        from mindflow_backend.agents.tools.system.shell_executor_v2 import (
            ShellExecutorToolV2
        )

        assert ShellExecutorToolV2 is not None

    @pytest.mark.asyncio
    async def test_file_read_v2_basic(self, tmp_path):
        """Test FileReadToolV2 basic execution."""
        from mindflow_backend.agents.tools.filesystem.file_operations_v2 import (
            FileReadToolV2
        )

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\n")

        tool = FileReadToolV2(root_dir=str(tmp_path))
        result = await tool.execute(file_path=str(test_file))

        assert result["success"] is True
        assert "Hello World" in result["content"]

    @pytest.mark.asyncio
    async def test_shell_executor_v2_basic(self):
        """Test ShellExecutorToolV2 basic execution."""
        from mindflow_backend.agents.tools.system.shell_executor_v2 import (
            ShellExecutorToolV2
        )

        tool = ShellExecutorToolV2()
        result = await tool.execute(command="echo 'test'")

        assert result["success"] is True
        assert "test" in result["stdout"]
        assert "semantic_type" in result
        assert "security_level" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
