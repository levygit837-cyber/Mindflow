"""Unit tests for file history module.

Tests snapshot creation, restoration, listing, and cleanup functionality.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.integrations.file_history import (
    FileHistoryStore,
    get_file_history,
    get_history_store,
    rollback_file,
    track_file_edit,
)


class TestFileHistoryStore:
    """Test FileHistoryStore class."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create test store."""
        history_dir = tmp_path / "history"
        return FileHistoryStore(history_dir=str(history_dir))

    @pytest.fixture
    def test_file(self, tmp_path):
        """Create test file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original content")
        return test_file

    def test_create_snapshot_success(self, store, test_file):
        """Test successful snapshot creation."""
        result = store.create_snapshot(str(test_file), "edit", {"user": "test"})

        assert result["success"] is True
        assert "snapshot_id" in result
        assert "snapshot_path" in result
        assert "file_hash" in result
        assert Path(result["snapshot_path"]).exists()

    def test_create_snapshot_nonexistent_file(self, store, tmp_path):
        """Test snapshot creation for nonexistent file."""
        result = store.create_snapshot(
            str(tmp_path / "nonexistent.txt"),
            "edit"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_list_snapshots_empty(self, store, test_file):
        """Test listing snapshots when none exist."""
        snapshots = store.list_snapshots(str(test_file))
        assert len(snapshots) == 0

    def test_list_snapshots_multiple(self, store, test_file):
        """Test listing multiple snapshots."""
        # Create multiple snapshots
        store.create_snapshot(str(test_file), "edit1")
        time.sleep(0.01)  # Ensure different timestamps
        store.create_snapshot(str(test_file), "edit2")
        time.sleep(0.01)
        store.create_snapshot(str(test_file), "edit3")

        snapshots = store.list_snapshots(str(test_file))

        assert len(snapshots) == 3
        # Should be sorted newest first
        assert snapshots[0]["operation"] == "edit3"
        assert snapshots[1]["operation"] == "edit2"
        assert snapshots[2]["operation"] == "edit1"

    def test_list_snapshots_filtered_by_file(self, store, tmp_path):
        """Test listing snapshots filtered by file path."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        store.create_snapshot(str(file1), "edit")
        store.create_snapshot(str(file2), "edit")

        snapshots1 = store.list_snapshots(str(file1))
        snapshots2 = store.list_snapshots(str(file2))

        assert len(snapshots1) == 1
        assert len(snapshots2) == 1
        assert snapshots1[0]["original_path"] == str(file1.resolve())
        assert snapshots2[0]["original_path"] == str(file2.resolve())

    def test_get_snapshot_success(self, store, test_file):
        """Test getting snapshot by ID."""
        create_result = store.create_snapshot(str(test_file), "edit")
        snapshot_id = create_result["snapshot_id"]

        get_result = store.get_snapshot(snapshot_id)

        assert get_result["success"] is True
        assert "metadata" in get_result
        assert "snapshot_path" in get_result
        assert get_result["metadata"]["operation"] == "edit"

    def test_get_snapshot_not_found(self, store):
        """Test getting nonexistent snapshot."""
        result = store.get_snapshot("nonexistent_id")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_restore_snapshot_success(self, store, test_file):
        """Test successful snapshot restoration."""
        original_content = test_file.read_text()

        # Create snapshot
        create_result = store.create_snapshot(str(test_file), "edit")
        snapshot_id = create_result["snapshot_id"]

        # Modify file
        test_file.write_text("Modified content")
        assert test_file.read_text() != original_content

        # Restore
        restore_result = store.restore_snapshot(snapshot_id)

        assert restore_result["success"] is True
        assert test_file.read_text() == original_content

    def test_restore_snapshot_to_different_path(self, store, test_file, tmp_path):
        """Test restoring snapshot to different path."""
        # Create snapshot
        create_result = store.create_snapshot(str(test_file), "edit")
        snapshot_id = create_result["snapshot_id"]

        # Restore to different path
        target_path = tmp_path / "restored.txt"
        restore_result = store.restore_snapshot(snapshot_id, str(target_path))

        assert restore_result["success"] is True
        assert target_path.exists()
        assert target_path.read_text() == test_file.read_text()

    def test_delete_snapshot_success(self, store, test_file):
        """Test successful snapshot deletion."""
        create_result = store.create_snapshot(str(test_file), "edit")
        snapshot_id = create_result["snapshot_id"]

        # Verify snapshot exists
        assert store.get_snapshot(snapshot_id)["success"] is True

        # Delete
        delete_result = store.delete_snapshot(snapshot_id)

        assert delete_result["success"] is True
        assert len(delete_result["deleted_files"]) > 0

        # Verify snapshot no longer exists
        assert store.get_snapshot(snapshot_id)["success"] is False

    def test_delete_snapshot_not_found(self, store):
        """Test deleting nonexistent snapshot."""
        result = store.delete_snapshot("nonexistent_id")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_cleanup_old_snapshots(self, store, test_file):
        """Test cleanup of old snapshots."""
        # Create snapshot
        create_result = store.create_snapshot(str(test_file), "edit")
        snapshot_path = Path(create_result["snapshot_path"])

        # Manually set old mtime (simulate old snapshot)
        old_time = time.time() - (31 * 86400)  # 31 days ago
        snapshot_path.touch()
        import os
        os.utime(snapshot_path, (old_time, old_time))

        # Also update metadata file
        metadata_path = snapshot_path.with_suffix('.json')
        os.utime(metadata_path, (old_time, old_time))

        # Cleanup
        cleanup_result = store.cleanup_old_snapshots(max_age_days=30)

        assert cleanup_result["success"] is True
        assert cleanup_result["deleted_count"] >= 1


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_track_file_edit(self, tmp_path):
        """Test track_file_edit convenience function."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = track_file_edit(str(test_file), "edit", {"user": "test"})

        assert result["success"] is True
        assert "snapshot_id" in result

    def test_get_file_history(self, tmp_path):
        """Test get_file_history convenience function."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Create some history
        track_file_edit(str(test_file), "edit1")
        track_file_edit(str(test_file), "edit2")

        history = get_file_history(str(test_file))

        assert len(history) >= 2

    def test_rollback_file(self, tmp_path):
        """Test rollback_file convenience function."""
        test_file = tmp_path / "test.txt"
        original_content = "original"
        test_file.write_text(original_content)

        # Create snapshot
        snapshot_result = track_file_edit(str(test_file), "edit")
        snapshot_id = snapshot_result["snapshot_id"]

        # Modify file
        test_file.write_text("modified")

        # Rollback
        rollback_result = rollback_file(snapshot_id)

        assert rollback_result["success"] is True
        assert test_file.read_text() == original_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
