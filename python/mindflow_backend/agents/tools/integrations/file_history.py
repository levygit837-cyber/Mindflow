"""File history tracking for MindFlow tools.

Provides snapshot creation, history rollback, and change tracking
for file operations.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ============================================================================
# File History Storage
# ============================================================================

class FileHistoryStore:
    """Store and manage file history snapshots."""

    def __init__(self, history_dir: str | None = None):
        """Initialize file history store.

        Args:
            history_dir: Directory to store history snapshots
                        (default: .mindflow/history)
        """
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            self.history_dir = Path.home() / ".mindflow" / "history"

        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, file_path: str) -> str:
        """Get SHA256 hash of file content.

        Args:
            file_path: Path to the file

        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_snapshot_path(self, file_path: str, timestamp: str) -> Path:
        """Get path for snapshot storage.

        Args:
            file_path: Original file path
            timestamp: Timestamp string

        Returns:
            Path to snapshot file
        """
        # Create safe filename from original path
        safe_name = file_path.replace('/', '_').replace('\\', '_')
        snapshot_name = f"{safe_name}_{timestamp}"
        return self.history_dir / snapshot_name

    def create_snapshot(
        self,
        file_path: str,
        operation: str,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a snapshot of a file before modification.

        Args:
            file_path: Path to the file
            operation: Operation being performed (write, edit, delete)
            metadata: Additional metadata to store

        Returns:
            Dict with snapshot information:
            - success: bool
            - snapshot_id: str
            - snapshot_path: str
            - file_hash: str
            - timestamp: str
            - error: str (if failed)
        """
        try:
            abs_path = Path(file_path).resolve()

            if not abs_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

            # Get file hash
            file_hash = self._get_file_hash(str(abs_path))

            # Create snapshot path
            snapshot_path = self._get_snapshot_path(str(abs_path), timestamp)

            # Copy file to snapshot
            shutil.copy2(str(abs_path), str(snapshot_path))

            # Create metadata file
            metadata_dict = {
                "original_path": str(abs_path),
                "operation": operation,
                "timestamp": timestamp,
                "file_hash": file_hash,
                "file_size": abs_path.stat().st_size,
                "metadata": metadata or {}
            }

            metadata_path = snapshot_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata_dict, f, indent=2)

            _logger.info(f"Created snapshot for {file_path}: {snapshot_path}")

            return {
                "success": True,
                "snapshot_id": timestamp,
                "snapshot_path": str(snapshot_path),
                "metadata_path": str(metadata_path),
                "file_hash": file_hash,
                "timestamp": timestamp
            }

        except Exception as e:
            _logger.error(f"Error creating snapshot: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Exception: {e}"
            }

    def list_snapshots(self, file_path: str | None = None) -> list[dict[str, Any]]:
        """List all snapshots, optionally filtered by file path.

        Args:
            file_path: Optional file path to filter by

        Returns:
            List of snapshot metadata dicts
        """
        snapshots = []

        try:
            # Find all metadata files
            for metadata_file in self.history_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                    # Filter by file path if specified
                    if file_path:
                        abs_path = str(Path(file_path).resolve())
                        if metadata.get("original_path") != abs_path:
                            continue

                    snapshots.append(metadata)

                except Exception as e:
                    _logger.warning(f"Error reading metadata {metadata_file}: {e}")

            # Sort by timestamp (newest first)
            snapshots.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        except Exception as e:
            _logger.error(f"Error listing snapshots: {e}", exc_info=True)

        return snapshots

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Get snapshot by ID.

        Args:
            snapshot_id: Snapshot ID (timestamp)

        Returns:
            Dict with snapshot information or error
        """
        try:
            # Find metadata file with matching timestamp
            for metadata_file in self.history_dir.glob(f"*_{snapshot_id}.json"):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

                snapshot_file = metadata_file.with_suffix('')
                if snapshot_file.exists():
                    return {
                        "success": True,
                        "metadata": metadata,
                        "snapshot_path": str(snapshot_file)
                    }

            return {
                "success": False,
                "error": f"Snapshot not found: {snapshot_id}"
            }

        except Exception as e:
            _logger.error(f"Error getting snapshot: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Exception: {e}"
            }

    def restore_snapshot(
        self,
        snapshot_id: str,
        target_path: str | None = None
    ) -> dict[str, Any]:
        """Restore a file from snapshot.

        Args:
            snapshot_id: Snapshot ID to restore
            target_path: Optional target path (default: original path)

        Returns:
            Dict with restore information:
            - success: bool
            - restored_path: str
            - error: str (if failed)
        """
        try:
            # Get snapshot
            snapshot_info = self.get_snapshot(snapshot_id)
            if not snapshot_info.get("success"):
                return snapshot_info

            metadata = snapshot_info["metadata"]
            snapshot_path = snapshot_info["snapshot_path"]

            # Determine target path
            if target_path:
                restore_path = Path(target_path).resolve()
            else:
                restore_path = Path(metadata["original_path"])

            # Create parent directories if needed
            restore_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy snapshot to target
            shutil.copy2(snapshot_path, str(restore_path))

            _logger.info(f"Restored snapshot {snapshot_id} to {restore_path}")

            return {
                "success": True,
                "restored_path": str(restore_path),
                "snapshot_id": snapshot_id,
                "original_path": metadata["original_path"]
            }

        except Exception as e:
            _logger.error(f"Error restoring snapshot: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Exception: {e}"
            }

    def delete_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Delete a snapshot.

        Args:
            snapshot_id: Snapshot ID to delete

        Returns:
            Dict with deletion result
        """
        try:
            deleted_files = []

            # Find and delete snapshot files
            for file in self.history_dir.glob(f"*_{snapshot_id}*"):
                file.unlink()
                deleted_files.append(str(file))

            if not deleted_files:
                return {
                    "success": False,
                    "error": f"Snapshot not found: {snapshot_id}"
                }

            _logger.info(f"Deleted snapshot {snapshot_id}")

            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "deleted_files": deleted_files
            }

        except Exception as e:
            _logger.error(f"Error deleting snapshot: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Exception: {e}"
            }

    def cleanup_old_snapshots(self, max_age_days: int = 30) -> dict[str, Any]:
        """Clean up snapshots older than specified age.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Dict with cleanup results
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.now().timestamp() - (max_age_days * 86400)

            for metadata_file in self.history_dir.glob("*.json"):
                try:
                    # Check file modification time
                    if metadata_file.stat().st_mtime < cutoff_time:
                        # Delete metadata and snapshot
                        snapshot_file = metadata_file.with_suffix('')
                        if snapshot_file.exists():
                            snapshot_file.unlink()
                        metadata_file.unlink()
                        deleted_count += 1

                except Exception as e:
                    _logger.warning(f"Error deleting old snapshot {metadata_file}: {e}")

            _logger.info(f"Cleaned up {deleted_count} old snapshots")

            return {
                "success": True,
                "deleted_count": deleted_count,
                "max_age_days": max_age_days
            }

        except Exception as e:
            _logger.error(f"Error cleaning up snapshots: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Exception: {e}"
            }


# ============================================================================
# Global History Store
# ============================================================================

_global_history_store: FileHistoryStore | None = None


def get_history_store() -> FileHistoryStore:
    """Get global file history store instance.

    Returns:
        FileHistoryStore instance
    """
    global _global_history_store
    if _global_history_store is None:
        _global_history_store = FileHistoryStore()
    return _global_history_store


# ============================================================================
# Convenience Functions
# ============================================================================

def track_file_edit(
    file_path: str,
    operation: str = "edit",
    metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Track a file edit by creating a snapshot.

    Args:
        file_path: Path to the file
        operation: Operation type
        metadata: Additional metadata

    Returns:
        Snapshot creation result
    """
    store = get_history_store()
    return store.create_snapshot(file_path, operation, metadata)


def rollback_file(snapshot_id: str, target_path: str | None = None) -> dict[str, Any]:
    """Rollback a file to a previous snapshot.

    Args:
        snapshot_id: Snapshot ID to restore
        target_path: Optional target path

    Returns:
        Restore result
    """
    store = get_history_store()
    return store.restore_snapshot(snapshot_id, target_path)


def get_file_history(file_path: str) -> list[dict[str, Any]]:
    """Get history for a specific file.

    Args:
        file_path: Path to the file

    Returns:
        List of snapshots for the file
    """
    store = get_history_store()
    return store.list_snapshots(file_path)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "FileHistoryStore",
    "get_history_store",
    "track_file_edit",
    "rollback_file",
    "get_file_history",
]
