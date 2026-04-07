"""Snapshot storage layer with PostgreSQL persistence and JSON fallback.

Provides persistent storage for browser snapshots with automatic fallback
to JSON file storage when PostgreSQL is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser.snapshot_models import Snapshot, SnapshotData

_logger = get_logger(__name__)


class SnapshotStorageError(Exception):
    """Base error for snapshot storage operations."""
    pass


class PostgresUnavailableError(SnapshotStorageError):
    """Raised when PostgreSQL is unavailable."""
    pass


class SnapshotStorage:
    """Storage layer for browser snapshots with PostgreSQL + JSON fallback.
    
    This storage layer:
    - Primary: PostgreSQL for persistent storage
    - Fallback: JSON files when PostgreSQL unavailable
    - Automatic retry with fallback
    - TTL-based cleanup
    """
    
    def __init__(
        self,
        postgres_dsn: str | None = None,
        json_fallback_dir: str | None = None,
        default_ttl_seconds: int = 3600,
    ):
        """Initialize snapshot storage.
        
        Args:
            postgres_dsn: PostgreSQL connection string
            json_fallback_dir: Directory for JSON fallback storage
            default_ttl_seconds: Default TTL for snapshots
        """
        self.postgres_dsn = postgres_dsn or os.getenv(
            "DATABASE_URL",
            os.getenv("POSTGRES_DSN", ""),
        )
        self.json_fallback_dir = Path(
            json_fallback_dir or os.getenv("SNAPSHOT_FALLBACK_DIR", "/tmp/mindflow_snapshots")
        )
        self.default_ttl_seconds = default_ttl_seconds
        
        # Create fallback directory if needed
        self.json_fallback_dir.mkdir(parents=True, exist_ok=True)
        
        # PostgreSQL connection pool (lazy initialization)
        self._postgres_pool: Any = None
        self._postgres_available = True
        
        # Lock for concurrent access
        self._lock = asyncio.Lock()
    
    async def _get_postgres_pool(self) -> Any:
        """Get or create PostgreSQL connection pool.
        
        Returns:
            Connection pool or None if unavailable
        """
        if not self._postgres_available or not ASYNCPG_AVAILABLE:
            return None
        
        if self._postgres_pool is None:
            try:
                self._postgres_pool = await asyncpg.create_pool(
                    self.postgres_dsn,
                    min_size=1,
                    max_size=10,
                    command_timeout=30,
                )
                _logger.info("postgres_pool_created")
            except Exception as exc:
                _logger.error("postgres_pool_creation_failed", error=str(exc))
                self._postgres_available = False
                return None
        
        return self._postgres_pool
    
    async def save_snapshot(
        self,
        snapshot: Snapshot,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Save a snapshot to storage.
        
        Args:
            snapshot: Snapshot to save
            ttl_seconds: Time-to-live in seconds (uses default if None)
            
        Returns:
            bool: True if saved successfully
        """
        # Validate snapshot data before saving
        try:
            snapshot.validate()
        except Exception as exc:
            _logger.error(
                "snapshot_validation_failed",
                snapshot_id=snapshot.snapshot_id,
                error=str(exc),
            )
            return False
        
        ttl = ttl_seconds or self.default_ttl_seconds
        expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None
        
        async with self._lock:
            # Try PostgreSQL first
            if self.postgres_dsn:
                try:
                    pool = await self._get_postgres_pool()
                    if pool:
                        await self._save_to_postgres(snapshot, expires_at, pool)
                        _logger.info(
                            "snapshot_saved_to_postgres",
                            snapshot_id=snapshot.snapshot_id,
                        )
                        return True
                except Exception as exc:
                    _logger.warning(
                        "postgres_save_failed_using_fallback",
                        snapshot_id=snapshot.snapshot_id,
                        error=str(exc),
                    )
            
            # Fallback to JSON
            try:
                await self._save_to_json(snapshot, expires_at)
                _logger.info(
                    "snapshot_saved_to_json_fallback",
                    snapshot_id=snapshot.snapshot_id,
                )
                return True
            except Exception as exc:
                _logger.error(
                    "json_fallback_save_failed",
                    snapshot_id=snapshot.snapshot_id,
                    error=str(exc),
                )
                return False
    
    async def _save_to_postgres(
        self,
        snapshot: Snapshot,
        expires_at: datetime | None,
        pool: Any,
    ) -> None:
        """Save snapshot to PostgreSQL.
        
        Args:
            snapshot: Snapshot to save
            expires_at: Expiration timestamp
            pool: PostgreSQL connection pool
        """
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO browser_snapshots 
                (snapshot_id, browser_id, url, cookies, local_storage, 
                 session_storage, page_state, created_at, expires_at, is_active, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (snapshot_id) DO UPDATE SET
                    url = EXCLUDED.url,
                    cookies = EXCLUDED.cookies,
                    local_storage = EXCLUDED.local_storage,
                    session_storage = EXCLUDED.session_storage,
                    page_state = EXCLUDED.page_state,
                    expires_at = EXCLUDED.expires_at,
                    is_active = TRUE,
                    metadata = EXCLUDED.metadata
                """,
                snapshot.snapshot_id,
                snapshot.browser_id,
                snapshot.url,
                json.dumps(snapshot.cookies),
                json.dumps(snapshot.local_storage),
                json.dumps(snapshot.session_storage),
                json.dumps(snapshot.page_state),
                snapshot.created_at,
                expires_at,
                True,
                json.dumps({}),
            )
    
    async def _save_to_json(
        self,
        snapshot: Snapshot,
        expires_at: datetime | None,
    ) -> None:
        """Save snapshot to JSON file.
        
        Args:
            snapshot: Snapshot to save
            expires_at: Expiration timestamp
        """
        snapshot_data = {
            "snapshot_id": snapshot.snapshot_id,
            "browser_id": snapshot.browser_id,
            "url": snapshot.url,
            "cookies": snapshot.cookies,
            "local_storage": snapshot.local_storage,
            "session_storage": snapshot.session_storage,
            "page_state": snapshot.page_state,
            "created_at": snapshot.created_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }
        
        file_path = self.json_fallback_dir / f"{snapshot.snapshot_id}.json"
        with open(file_path, "w") as f:
            json.dump(snapshot_data, f, indent=2)
    
    async def load_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """Load a snapshot from storage.
        
        Args:
            snapshot_id: ID of snapshot to load
            
        Returns:
            Snapshot or None if not found
        """
        async with self._lock:
            # Try PostgreSQL first
            if self.postgres_dsn:
                try:
                    pool = await self._get_postgres_pool()
                    if pool:
                        snapshot = await self._load_from_postgres(snapshot_id, pool)
                        if snapshot:
                            _logger.info(
                                "snapshot_loaded_from_postgres",
                                snapshot_id=snapshot_id,
                            )
                            return snapshot
                except Exception as exc:
                    _logger.warning(
                        "postgres_load_failed_using_fallback",
                        snapshot_id=snapshot_id,
                        error=str(exc),
                    )
            
            # Fallback to JSON
            try:
                snapshot = await self._load_from_json(snapshot_id)
                if snapshot:
                    _logger.info(
                        "snapshot_loaded_from_json_fallback",
                        snapshot_id=snapshot_id,
                    )
                    return snapshot
            except Exception as exc:
                _logger.error(
                    "json_fallback_load_failed",
                    snapshot_id=snapshot_id,
                    error=str(exc),
                )
            
            return None
    
    async def _load_from_postgres(
        self,
        snapshot_id: str,
        pool: Any,
    ) -> Snapshot | None:
        """Load snapshot from PostgreSQL.
        
        Args:
            snapshot_id: ID of snapshot to load
            pool: PostgreSQL connection pool
            
        Returns:
            Snapshot or None if not found
        """
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT snapshot_id, browser_id, url, cookies, local_storage,
                       session_storage, page_state, created_at
                FROM browser_snapshots
                WHERE snapshot_id = $1 AND is_active = TRUE
                """,
                snapshot_id,
            )
            
            if not row:
                return None
            
            return Snapshot(
                snapshot_id=row["snapshot_id"],
                browser_id=row["browser_id"],
                url=row["url"],
                cookies=json.loads(row["cookies"]) if row["cookies"] else [],
                local_storage=json.loads(row["local_storage"]) if row["local_storage"] else {},
                session_storage=json.loads(row["session_storage"]) if row["session_storage"] else {},
                page_state=json.loads(row["page_state"]) if row["page_state"] else {},
                created_at=row["created_at"],
            )
    
    async def _load_from_json(self, snapshot_id: str) -> Snapshot | None:
        """Load snapshot from JSON file.
        
        Args:
            snapshot_id: ID of snapshot to load
            
        Returns:
            Snapshot or None if not found
        """
        file_path = self.json_fallback_dir / f"{snapshot_id}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Check if expired
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                file_path.unlink()  # Remove expired file
                return None
        
        return Snapshot(
            snapshot_id=data["snapshot_id"],
            browser_id=data["browser_id"],
            url=data["url"],
            cookies=data["cookies"],
            local_storage=data["local_storage"],
            session_storage=data["session_storage"],
            page_state=data["page_state"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot from storage.
        
        Args:
            snapshot_id: ID of snapshot to delete
            
        Returns:
            bool: True if deleted successfully
        """
        async with self._lock:
            deleted = False
            
            # Try PostgreSQL
            if self.postgres_dsn:
                try:
                    pool = await self._get_postgres_pool()
                    if pool:
                        async with pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE browser_snapshots SET is_active = FALSE WHERE snapshot_id = $1",
                                snapshot_id,
                            )
                            deleted = True
                            _logger.info("snapshot_deleted_from_postgres", snapshot_id=snapshot_id)
                except Exception as exc:
                    _logger.warning("postgres_delete_failed", error=str(exc))
            
            # Also try JSON fallback
            try:
                file_path = self.json_fallback_dir / f"{snapshot_id}.json"
                if file_path.exists():
                    file_path.unlink()
                    deleted = True
                    _logger.info("snapshot_deleted_from_json", snapshot_id=snapshot_id)
            except Exception as exc:
                _logger.warning("json_delete_failed", error=str(exc))
            
            return deleted
    
    async def cleanup_expired_snapshots(self) -> int:
        """Clean up expired snapshots.
        
        Returns:
            int: Number of snapshots cleaned up
        """
        cleaned_count = 0
        
        # Cleanup PostgreSQL
        if self.postgres_dsn:
            try:
                pool = await self._get_postgres_pool()
                if pool:
                    async with pool.acquire() as conn:
                        result = await conn.execute(
                            "SELECT cleanup_expired_snapshots()",
                        )
                        cleaned_count = int(result.split()[-1])
                        _logger.info("postgres_cleanup_completed", count=cleaned_count)
            except Exception as exc:
                _logger.warning("postgres_cleanup_failed", error=str(exc))
        
        # Cleanup JSON files
        try:
            now = datetime.utcnow()
            for file_path in self.json_fallback_dir.glob("*.json"):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    
                    if data.get("expires_at"):
                        expires_at = datetime.fromisoformat(data["expires_at"])
                        if now > expires_at:
                            file_path.unlink()
                            cleaned_count += 1
                except Exception as exc:
                    _logger.warning("json_file_cleanup_failed", file=str(file_path), error=str(exc))
        except Exception as exc:
            _logger.warning("json_dir_cleanup_failed", error=str(exc))
        
        return cleaned_count
    
    async def close(self) -> None:
        """Close storage connections."""
        if self._postgres_pool:
            await self._postgres_pool.close()
            self._postgres_pool = None
            _logger.info("postgres_pool_closed")
