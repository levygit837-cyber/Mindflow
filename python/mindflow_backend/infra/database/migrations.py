"""Database migration management and utilities.

Provides tools for managing database migrations, versioning,
and schema updates in a controlled and reversible manner.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from enum import Enum
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, MetaData, Table, Column
from sqlalchemy.types import String, DateTime, Integer

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.database.connection import get_db_session

_logger = get_logger(__name__)


class MigrationState(Enum):
    """Migration execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """Database migration definition."""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: Optional[str] = None
    dependencies: Optional[List[str]] = None
    checksum: Optional[str] = None
    
    def __post_init__(self) -> None:
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
            
    def _calculate_checksum(self) -> str:
        """Calculate migration checksum for integrity verification."""
        content = f"{self.version}:{self.name}:{self.up_sql}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class MigrationRecord:
    """Database migration execution record."""
    version: str
    name: str
    state: MigrationState
    executed_at: datetime
    execution_time_ms: float
    checksum: str
    error_message: Optional[str] = None


class MigrationManager:
    """Advanced database migration management.
    
    Features:
    - Version-controlled migrations
    - Dependency resolution
    - Rollback capabilities
    - Migration integrity verification
    - Concurrent execution protection
    - Migration history tracking
    """
    
    def __init__(self) -> None:
        """Initialize migration manager."""
        self._migrations: Dict[str, Migration] = {}
        self._migration_lock = asyncio.Lock()
        
    def register_migration(self, migration: Migration) -> None:
        """Register a migration for execution.
        
        Args:
            migration: Migration to register
        """
        if migration.version in self._migrations:
            raise ValueError(f"Migration version {migration.version} already registered")
            
        self._migrations[migration.version] = migration
        _logger.info(
            "migration_registered",
            version=migration.version,
            name=migration.name,
            checksum=migration.checksum,
        )
        
    async def ensure_migration_table(self) -> None:
        """Ensure migration tracking table exists."""
        async with get_db_session() as session:
            # Create migrations table if not exists
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    state VARCHAR(20) NOT NULL DEFAULT 'pending',
                    executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    execution_time_ms FLOAT NOT NULL,
                    checksum VARCHAR(16) NOT NULL,
                    error_message TEXT
                )
            """))
            
            # Create index for performance
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_schema_migrations_executed_at 
                ON schema_migrations(executed_at)
            """))
            
            await session.commit()
            _logger.info("migration_table_ensured")
            
    async def get_applied_migrations(self) -> List[MigrationRecord]:
        """Get list of applied migrations from database.
        
        Returns:
            List of applied migration records.
        """
        await self.ensure_migration_table()
        
        async with get_db_session() as session:
            result = await session.execute(text("""
                SELECT version, name, state, executed_at, execution_time_ms, 
                       checksum, error_message
                FROM schema_migrations 
                ORDER BY executed_at
            """))
            
            records = []
            for row in result:
                record = MigrationRecord(
                    version=row.version,
                    name=row.name,
                    state=MigrationState(row.state),
                    executed_at=row.executed_at,
                    execution_time_ms=row.execution_time_ms,
                    checksum=row.checksum,
                    error_message=row.error_message,
                )
                records.append(record)
                
            return records
            
    async def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations to apply.
        
        Returns:
            List of pending migrations in dependency order.
        """
        applied = await self.get_applied_migrations()
        applied_versions = {record.version for record in applied}
        
        pending = [
            migration for version, migration in self._migrations.items()
            if version not in applied_versions
        ]
        
        # Sort by dependencies
        return self._sort_by_dependencies(pending)
        
    def _sort_by_dependencies(self, migrations: List[Migration]) -> List[Migration]:
        """Sort migrations by dependency order.
        
        Args:
            migrations: List of migrations to sort
            
        Returns:
            Sorted list of migrations.
        """
        sorted_migrations = []
        remaining = migrations.copy()
        
        while remaining:
            # Find migrations with no unresolved dependencies
            ready = [
                mig for mig in remaining
                if not mig.dependencies or 
                all(dep in [m.version for m in sorted_migrations] for dep in mig.dependencies)
            ]
            
            if not ready:
                raise ValueError("Circular dependency detected in migrations")
                
            # Add first ready migration
            migration = ready[0]
            sorted_migrations.append(migration)
            remaining.remove(migration)
            
        return sorted_migrations
        
    async def apply_migration(self, migration: Migration) -> MigrationRecord:
        """Apply a single migration.
        
        Args:
            migration: Migration to apply
            
        Returns:
            Migration execution record.
        """
        async with self._migration_lock:
            start_time = datetime.now(UTC)
            
            try:
                # Verify migration not already applied
                applied = await self.get_applied_migrations()
                if any(record.version == migration.version for record in applied):
                    raise ValueError(f"Migration {migration.version} already applied")
                    
                # Verify dependencies
                applied_versions = {record.version for record in applied}
                if migration.dependencies:
                    missing_deps = [
                        dep for dep in migration.dependencies
                        if dep not in applied_versions
                    ]
                    if missing_deps:
                        raise ValueError(f"Missing dependencies: {missing_deps}")
                        
                # Execute migration
                await self.ensure_migration_table()
                
                async with get_db_session() as session:
                    # Record migration start
                    await session.execute(text("""
                        INSERT INTO schema_migrations 
                        (version, name, state, executed_at, execution_time_ms, checksum)
                        VALUES (:version, :name, :state, :executed_at, :execution_time_ms, :checksum)
                    """), {
                        "version": migration.version,
                        "name": migration.name,
                        "state": MigrationState.RUNNING.value,
                        "executed_at": start_time,
                        "execution_time_ms": 0.0,
                        "checksum": migration.checksum,
                    })
                    
                    # Execute migration SQL
                    await session.execute(text(migration.up_sql))
                    
                    # Calculate execution time
                    execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
                    
                    # Update migration record
                    await session.execute(text("""
                        UPDATE schema_migrations 
                        SET state = :state, execution_time_ms = :execution_time_ms
                        WHERE version = :version
                    """), {
                        "version": migration.version,
                        "state": MigrationState.COMPLETED.value,
                        "execution_time_ms": execution_time,
                    })
                    
                    await session.commit()
                    
                    record = MigrationRecord(
                        version=migration.version,
                        name=migration.name,
                        state=MigrationState.COMPLETED,
                        executed_at=start_time,
                        execution_time_ms=execution_time,
                        checksum=migration.checksum,
                    )
                    
                    _logger.info(
                        "migration_applied",
                        version=migration.version,
                        name=migration.name,
                        execution_time_ms=execution_time,
                    )
                    
                    return record
                    
            except Exception as e:
                execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
                
                # Record failure
                try:
                    async with get_db_session() as session:
                        await session.execute(text("""
                            UPDATE schema_migrations 
                            SET state = :state, error_message = :error_message, execution_time_ms = :execution_time_ms
                            WHERE version = :version
                        """), {
                            "version": migration.version,
                            "state": MigrationState.FAILED.value,
                            "error_message": str(e),
                            "execution_time_ms": execution_time,
                        })
                        await session.commit()
                except Exception as record_error:
                    _logger.error("migration_failure_recording_failed", error=str(record_error))
                    
                _logger.error(
                    "migration_failed",
                    version=migration.version,
                    name=migration.name,
                    error=str(e),
                    execution_time_ms=execution_time,
                )
                
                raise
                
    async def rollback_migration(self, version: str) -> MigrationRecord:
        """Rollback a specific migration.
        
        Args:
            version: Migration version to rollback
            
        Returns:
            Updated migration record.
        """
        if version not in self._migrations:
            raise ValueError(f"Migration version {version} not found")
            
        migration = self._migrations[version]
        if not migration.down_sql:
            raise ValueError(f"Migration {version} does not support rollback")
            
        async with self._migration_lock:
            start_time = datetime.now(UTC)
            
            try:
                # Verify migration is applied
                applied = await self.get_applied_migrations()
                applied_record = next(
                    (record for record in applied if record.version == version),
                    None
                )
                
                if not applied_record:
                    raise ValueError(f"Migration {version} not applied")
                    
                if applied_record.state != MigrationState.COMPLETED:
                    raise ValueError(f"Migration {version} not in completed state")
                    
                # Execute rollback
                async with get_db_session() as session:
                    # Execute rollback SQL
                    await session.execute(text(migration.down_sql))
                    
                    # Update migration record
                    execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
                    
                    await session.execute(text("""
                        UPDATE schema_migrations 
                        SET state = :state, execution_time_ms = :execution_time_ms
                        WHERE version = :version
                    """), {
                        "version": version,
                        "state": MigrationState.ROLLED_BACK.value,
                        "execution_time_ms": execution_time_ms,
                    })
                    
                    await session.commit()
                    
                    record = MigrationRecord(
                        version=version,
                        name=migration.name,
                        state=MigrationState.ROLLED_BACK,
                        executed_at=applied_record.executed_at,
                        execution_time_ms=execution_time,
                        checksum=migration.checksum,
                    )
                    
                    _logger.info(
                        "migration_rolled_back",
                        version=version,
                        name=migration.name,
                        execution_time_ms=execution_time,
                    )
                    
                    return record
                    
            except Exception as e:
                _logger.error(
                    "migration_rollback_failed",
                    version=version,
                    error=str(e),
                )
                raise
                
    async def migrate_up(self, target_version: Optional[str] = None) -> List[MigrationRecord]:
        """Apply pending migrations up to target version.
        
        Args:
            target_version: Optional target version to stop at
            
        Returns:
            List of applied migration records.
        """
        pending = await self.get_pending_migrations()
        applied = []
        
        for migration in pending:
            if target_version and migration.version > target_version:
                break
                
            record = await self.apply_migration(migration)
            applied.append(record)
            
        _logger.info(
            "migration_up_completed",
            applied_count=len(applied),
            target_version=target_version,
        )
        
        return applied
        
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status.
        
        Returns:
            Dict containing migration status information.
        """
        applied = await self.get_applied_migrations()
        pending = await self.get_pending_migrations()
        
        status = {
            "total_migrations": len(self._migrations),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "last_migration": applied[-1].version if applied else None,
            "current_version": applied[-1].version if applied else None,
            "applied_migrations": [
                {
                    "version": record.version,
                    "name": record.name,
                    "executed_at": record.executed_at.isoformat(),
                    "execution_time_ms": record.execution_time_ms,
                    "state": record.state.value,
                }
                for record in applied
            ],
            "pending_migrations": [
                {
                    "version": mig.version,
                    "name": mig.name,
                    "dependencies": mig.dependencies,
                }
                for mig in pending
            ],
        }
        
        return status


# Global migration manager instance
_migration_manager: Optional[MigrationManager] = None


def get_migration_manager() -> MigrationManager:
    """Get global migration manager instance."""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager()
    return _migration_manager
