"""Configuration storage backends for dynamic configuration.

Provides different storage options for configuration persistence
including memory, file, and database backends.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.grpc_internal.config import GrpcConfig
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ConfigStorage(ABC):
    """Abstract base class for configuration storage backends."""
    
    @abstractmethod
    async def load_config(self) -> GrpcConfig:
        """Load configuration from storage."""
        pass
    
    @abstractmethod
    async def save_config(self, config: GrpcConfig, version: str) -> str:
        """Save configuration to storage with version."""
        pass
    
    @abstractmethod
    async def load_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load configuration history."""
        pass
    
    @abstractmethod
    async def delete_config(self, version: str) -> bool:
        """Delete specific configuration version."""
        pass


class MemoryConfigStorage(ConfigStorage):
    """In-memory configuration storage."""
    
    def __init__(self):
        self._config: GrpcConfig | None = None
        self._history: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
    
    async def load_config(self) -> GrpcConfig:
        """Load configuration from memory."""
        async with self._lock:
            if self._config is None:
                # Return default configuration
                self._config = GrpcConfig()
            return self._config
    
    async def save_config(self, config: GrpcConfig, version: str) -> str:
        """Save configuration to memory."""
        async with self._lock:
            self._config = config
            
            # Add to history
            history_entry = {
                "version": version,
                "timestamp": datetime.now().isoformat(),
                "config": config.dict()
            }
            self._history.append(history_entry)
            
            # Limit history size
            if len(self._history) > 100:
                self._history = self._history[-100:]
            
            return version
    
    async def load_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load configuration history from memory."""
        async with self._lock:
            return self._history[-limit:] if limit > 0 else self._history
    
    async def delete_config(self, version: str) -> bool:
        """Delete configuration version from memory."""
        async with self._lock:
            self._history = [entry for entry in self._history if entry["version"] != version]
            return True


class FileConfigStorage(ConfigStorage):
    """File-based configuration storage."""
    
    def __init__(self, config_file: str = "grpc_config.json", history_dir: str = "grpc_config_history"):
        self.config_file = Path(config_file)
        self.history_dir = Path(history_dir)
        self._lock = asyncio.Lock()
        
        # Ensure directories exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    async def load_config(self) -> GrpcConfig:
        """Load configuration from file."""
        async with self._lock:
            try:
                if self.config_file.exists():
                    with open(self.config_file, encoding='utf-8') as f:
                        config_data = json.load(f)
                    return GrpcConfig(**config_data)
                else:
                    # Create default configuration
                    default_config = GrpcConfig()
                    await self.save_config(default_config, "initial")
                    return default_config
            except Exception as exc:
                _logger.error("file_config_load_failed", file=str(self.config_file), error=str(exc))
                return GrpcConfig()
    
    async def save_config(self, config: GrpcConfig, version: str) -> str:
        """Save configuration to file."""
        async with self._lock:
            try:
                # Save current configuration
                config_data = config.dict()
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, default=str)
                
                # Save to history
                history_file = self.history_dir / f"{version}.json"
                history_entry = {
                    "version": version,
                    "timestamp": datetime.now().isoformat(),
                    "config": config_data
                }
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(history_entry, f, indent=2, default=str)
                
                _logger.debug("config_saved_to_file", file=str(self.config_file), version=version)
                return version
                
            except Exception as exc:
                _logger.error("file_config_save_failed", file=str(self.config_file), error=str(exc))
                raise
    
    async def load_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load configuration history from files."""
        async with self._lock:
            try:
                history = []
                
                # Get all history files sorted by timestamp
                history_files = sorted(
                    self.history_dir.glob("*.json"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True
                )
                
                for history_file in history_files[:limit]:
                    try:
                        with open(history_file, encoding='utf-8') as f:
                            history_entry = json.load(f)
                        history.append(history_entry)
                    except Exception as exc:
                        _logger.warning("history_file_load_failed", file=str(history_file), error=str(exc))
                
                return history
                
            except Exception as exc:
                _logger.error("file_history_load_failed", error=str(exc))
                return []
    
    async def delete_config(self, version: str) -> bool:
        """Delete configuration version file."""
        async with self._lock:
            try:
                history_file = self.history_dir / f"{version}.json"
                if history_file.exists():
                    history_file.unlink()
                    return True
                return False
            except Exception as exc:
                _logger.error("file_config_delete_failed", version=version, error=str(exc))
                return False


class DatabaseConfigStorage(ConfigStorage):
    """Database-based configuration storage using SQLite."""
    
    def __init__(self, db_path: str = "grpc_config.db"):
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS grpc_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version TEXT UNIQUE NOT NULL,
                        config_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_current BOOLEAN DEFAULT FALSE
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_version ON grpc_config(version)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at ON grpc_config(created_at)
                """)
                
                conn.commit()
                
        except Exception as exc:
            _logger.error("database_init_failed", db_path=str(self.db_path), error=str(exc))
            raise
    
    async def load_config(self) -> GrpcConfig:
        """Load current configuration from database."""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT config_data FROM grpc_config 
                        WHERE is_current = TRUE 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    row = cursor.fetchone()
                    
                    if row:
                        config_data = json.loads(row[0])
                        return GrpcConfig(**config_data)
                    else:
                        # Create default configuration
                        default_config = GrpcConfig()
                        await self.save_config(default_config, "initial")
                        return default_config
                        
            except Exception as exc:
                _logger.error("database_config_load_failed", error=str(exc))
                return GrpcConfig()
    
    async def save_config(self, config: GrpcConfig, version: str) -> str:
        """Save configuration to database."""
        async with self._lock:
            try:
                config_data = json.dumps(config.dict(), default=str)
                
                with sqlite3.connect(self.db_path) as conn:
                    # Mark all existing configs as not current
                    conn.execute("""
                        UPDATE grpc_config SET is_current = FALSE
                    """)
                    
                    # Insert new configuration
                    conn.execute("""
                        INSERT OR REPLACE INTO grpc_config 
                        (version, config_data, is_current) 
                        VALUES (?, ?, TRUE)
                    """, (version, config_data))
                    
                    conn.commit()
                
                _logger.debug("config_saved_to_database", version=version)
                return version
                
            except Exception as exc:
                _logger.error("database_config_save_failed", error=str(exc))
                raise
    
    async def load_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load configuration history from database."""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT version, config_data, created_at 
                        FROM grpc_config 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (limit,))
                    
                    history = []
                    for row in cursor.fetchall():
                        history_entry = {
                            "version": row[0],
                            "config": json.loads(row[1]),
                            "timestamp": row[2]
                        }
                        history.append(history_entry)
                    
                    return history
                    
            except Exception as exc:
                _logger.error("database_history_load_failed", error=str(exc))
                return []
    
    async def delete_config(self, version: str) -> bool:
        """Delete configuration version from database."""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        DELETE FROM grpc_config WHERE version = ?
                    """, (version,))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    return deleted_count > 0
                    
            except Exception as exc:
                _logger.error("database_config_delete_failed", version=version, error=str(exc))
                return False
    
    async def get_current_version(self) -> str | None:
        """Get current configuration version."""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT version FROM grpc_config 
                        WHERE is_current = TRUE 
                        LIMIT 1
                    """)
                    row = cursor.fetchone()
                    return row[0] if row else None
                    
            except Exception as exc:
                _logger.error("database_current_version_failed", error=str(exc))
                return None


class PostgresConfigStorage(ConfigStorage):
    """PostgreSQL-based configuration storage."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._lock = asyncio.Lock()
    
    async def _get_connection(self):
        """Get database connection."""
        try:
            import asyncpg
            return await asyncpg.connect(self.connection_string)
        except ImportError:
            raise ImportError("asyncpg is required for PostgreSQL storage")
    
    async def _init_database(self):
        """Initialize database schema."""
        conn = await self._get_connection()
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS grpc_config (
                    id SERIAL PRIMARY KEY,
                    version TEXT UNIQUE NOT NULL,
                    config_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_current BOOLEAN DEFAULT FALSE
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_grpc_config_version ON grpc_config(version)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_grpc_config_created_at ON grpc_config(created_at)
            """)
            
        finally:
            await conn.close()
    
    async def load_config(self) -> GrpcConfig:
        """Load current configuration from PostgreSQL."""
        async with self._lock:
            try:
                conn = await self._get_connection()
                try:
                    row = await conn.fetchrow("""
                        SELECT config_data FROM grpc_config 
                        WHERE is_current = TRUE 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    
                    if row:
                        return GrpcConfig(**row['config_data'])
                    else:
                        # Create default configuration
                        default_config = GrpcConfig()
                        await self.save_config(default_config, "initial")
                        return default_config
                        
                finally:
                    await conn.close()
                    
            except Exception as exc:
                _logger.error("postgres_config_load_failed", error=str(exc))
                return GrpcConfig()
    
    async def save_config(self, config: GrpcConfig, version: str) -> str:
        """Save configuration to PostgreSQL."""
        async with self._lock:
            try:
                conn = await self._get_connection()
                try:
                    async with conn.transaction():
                        # Mark all existing configs as not current
                        await conn.execute("""
                            UPDATE grpc_config SET is_current = FALSE
                        """)
                        
                        # Insert new configuration
                        await conn.execute("""
                            INSERT INTO grpc_config 
                            (version, config_data, is_current) 
                            VALUES ($1, $2, TRUE)
                            ON CONFLICT (version) 
                            DO UPDATE SET 
                                config_data = EXCLUDED.config_data,
                                is_current = TRUE
                        """, version, config.dict())
                    
                    _logger.debug("config_saved_to_postgres", version=version)
                    return version
                    
                finally:
                    await conn.close()
                    
            except Exception as exc:
                _logger.error("postgres_config_save_failed", error=str(exc))
                raise
    
    async def load_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load configuration history from PostgreSQL."""
        async with self._lock:
            try:
                conn = await self._get_connection()
                try:
                    rows = await conn.fetch("""
                        SELECT version, config_data, created_at 
                        FROM grpc_config 
                        ORDER BY created_at DESC 
                        LIMIT $1
                    """, limit)
                    
                    history = []
                    for row in rows:
                        history_entry = {
                            "version": row['version'],
                            "config": dict(row['config_data']),
                            "timestamp": row['created_at'].isoformat()
                        }
                        history.append(history_entry)
                    
                    return history
                    
                finally:
                    await conn.close()
                    
            except Exception as exc:
                _logger.error("postgres_history_load_failed", error=str(exc))
                return []
    
    async def delete_config(self, version: str) -> bool:
        """Delete configuration version from PostgreSQL."""
        async with self._lock:
            try:
                conn = await self._get_connection()
                try:
                    result = await conn.execute("""
                        DELETE FROM grpc_config WHERE version = $1
                    """, version)
                    
                    return result != 'DELETE 0'
                    
                finally:
                    await conn.close()
                    
            except Exception as exc:
                _logger.error("postgres_config_delete_failed", version=version, error=str(exc))
                return False


# Factory function for creating storage backends
def create_config_storage(backend_type: str, **kwargs) -> ConfigStorage:
    """Create configuration storage backend."""
    backends = {
        "memory": MemoryConfigStorage,
        "file": FileConfigStorage,
        "sqlite": DatabaseConfigStorage,
        "postgres": PostgresConfigStorage,
    }
    
    if backend_type not in backends:
        raise ValueError(f"Unknown storage backend: {backend_type}. Available: {list(backends.keys())}")
    
    return backends[backend_type](**kwargs)
