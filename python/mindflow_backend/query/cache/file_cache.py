"""Session File Cache — persistent file state cache across turns.

Inspired by Claude Code's file state caching system:
- Caches file contents read during a session
- Avoids re-reading files that haven't changed
- Invalidates cache on file modifications (via mtime)
- Persists to disk for session recovery
- Integrates with AutoCompactService for post-compact restoration

Usage:
    cache = create_session_cache("session_123")
    content = await cache.get_or_read("/path/to/file.py")
    # Second read is instant (cached)
    content = await cache.get_or_read("/path/to/file.py")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default cache directory
DEFAULT_CACHE_DIR = "~/.mindflow/cache/file_cache"

# Maximum cache size per session (100MB)
MAX_CACHE_SIZE_BYTES = 100 * 1024 * 1024

# Maximum file size to cache (1MB)
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024

# Cache TTL (1 hour)
CACHE_TTL_SECONDS = 3600


@dataclass
class CachedFile:
    """A cached file entry."""

    path: str
    content: str
    content_hash: str
    mtime: float  # File modification time
    size: int
    token_estimate: int  # Approximate token count
    cached_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_stale(self, current_mtime: float) -> bool:
        """Check if cached entry is stale (file modified since cache)."""
        return current_mtime > self.mtime

    def is_expired(self, ttl: int = CACHE_TTL_SECONDS) -> bool:
        """Check if cache entry has expired."""
        return (time.time() - self.cached_at) > ttl

    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "path": self.path,
            "content": self.content,
            "content_hash": self.content_hash,
            "mtime": self.mtime,
            "size": self.size,
            "token_estimate": self.token_estimate,
            "cached_at": self.cached_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CachedFile:
        """Deserialize from dictionary."""
        return cls(
            path=data["path"],
            content=data["content"],
            content_hash=data["content_hash"],
            mtime=data["mtime"],
            size=data["size"],
            token_estimate=data["token_estimate"],
            cached_at=data.get("cached_at", time.time()),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed", time.time()),
        )


class SessionFileCache:
    """Persistent file state cache for a session.

    Features:
    - LRU eviction when cache exceeds size limit
    - Automatic invalidation on file modification (via mtime)
    - Disk persistence for session recovery
    - Token estimation for budget management
    - Integration with AutoCompactService

    Usage:
        cache = SessionFileCache(session_id="sess_123")
        
        # Read with caching
        content = await cache.get_or_read("/path/to/file.py")
        
        # Check cache stats
        stats = cache.get_stats()
        print(f"Cache hits: {stats['hits']}, misses: {stats['misses']}")
        
        # Persist to disk
        cache.save()
        
        # Load from disk
        cache.load()
    """

    def __init__(
        self,
        session_id: str,
        cache_dir: str | None = None,
        max_size_bytes: int = MAX_CACHE_SIZE_BYTES,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        auto_persist: bool = True,
    ) -> None:
        self.session_id = session_id
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR).expanduser()
        self.max_size_bytes = max_size_bytes
        self.max_file_size_bytes = max_file_size_bytes
        self.ttl_seconds = ttl_seconds
        self.auto_persist = auto_persist

        # In-memory cache
        self._cache: dict[str, CachedFile] = {}
        self._access_order: list[str] = []  # For LRU eviction

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0,
            "bytes_cached": 0,
        }

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_file(self) -> Path:
        """Path to the cache file on disk."""
        return self.cache_dir / f"{self.session_id}.json"

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count (rough: 1 token ≈ 4 chars)."""
        return len(content) // 4

    def _compute_hash(self, content: str) -> str:
        """Compute content hash for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _get_current_size(self) -> int:
        """Get current total cache size in bytes."""
        return sum(len(cf.content.encode("utf-8")) for cf in self._cache.values())

    def _evict_lru(self, required_bytes: int) -> None:
        """Evict least recently used entries to free space."""
        while self._access_order and self._get_current_size() + required_bytes > self.max_size_bytes:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                evicted = self._cache.pop(oldest_key)
                self._stats["evictions"] += 1
                self._stats["bytes_cached"] -= len(evicted.content.encode("utf-8"))
                logger.debug(
                    "file_cache_evicted",
                    path=oldest_key,
                    size=len(evicted.content.encode("utf-8")),
                )

    def _update_access_order(self, key: str) -> None:
        """Move key to end of access order (most recently used)."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    async def get_or_read(
        self,
        file_path: str,
        encoding: str = "utf-8",
    ) -> str | None:
        """Get file content from cache or read from disk.

        Args:
            file_path: Path to the file.
            encoding: File encoding (default: utf-8).

        Returns:
            File content as string, or None if file doesn't exist.
        """
        resolved_path = str(Path(file_path).resolve())

        # Check cache
        if resolved_path in self._cache:
            cached = self._cache[resolved_path]

            # Check if file still exists and get current mtime
            try:
                stat = os.stat(resolved_path)
                current_mtime = stat.st_mtime
            except OSError:
                # File was deleted
                self.invalidate(resolved_path)
                return None

            # Check if cache is valid (not stale, not expired)
            if not cached.is_stale(current_mtime) and not cached.is_expired(self.ttl_seconds):
                cached.touch()
                self._update_access_order(resolved_path)
                self._stats["hits"] += 1
                logger.debug("file_cache_hit", path=resolved_path)
                return cached.content
            else:
                # Cache is stale or expired
                self._stats["invalidations"] += 1
                logger.debug(
                    "file_cache_invalidated",
                    path=resolved_path,
                    reason="stale" if cached.is_stale(current_mtime) else "expired",
                )

        # Cache miss — read from disk
        self._stats["misses"] += 1
        return await self._read_and_cache(resolved_path, encoding)

    async def _read_and_cache(
        self,
        resolved_path: str,
        encoding: str = "utf-8",
    ) -> str | None:
        """Read file from disk and add to cache."""
        try:
            stat = os.stat(resolved_path)

            # Skip large files
            if stat.st_size > self.max_file_size_bytes:
                logger.debug(
                    "file_cache_skip_large",
                    path=resolved_path,
                    size=stat.st_size,
                    max_size=self.max_file_size_bytes,
                )
                # Read but don't cache
                with open(resolved_path, encoding=encoding) as f:
                    return f.read()

            # Read file
            with open(resolved_path, encoding=encoding) as f:
                content = f.read()

            # Create cache entry
            cached = CachedFile(
                path=resolved_path,
                content=content,
                content_hash=self._compute_hash(content),
                mtime=stat.st_mtime,
                size=stat.st_size,
                token_estimate=self._estimate_tokens(content),
            )

            # Evict if necessary
            content_bytes = len(content.encode("utf-8"))
            self._evict_lru(content_bytes)

            # Add to cache
            self._cache[resolved_path] = cached
            self._update_access_order(resolved_path)
            self._stats["bytes_cached"] += content_bytes

            logger.debug(
                "file_cache_added",
                path=resolved_path,
                size=stat.st_size,
                tokens=cached.token_estimate,
            )

            # Auto-persist if enabled
            if self.auto_persist:
                self.save()

            return content

        except FileNotFoundError:
            logger.debug("file_cache_not_found", path=resolved_path)
            return None
        except PermissionError:
            logger.warning("file_cache_permission_denied", path=resolved_path)
            return None
        except Exception as exc:
            logger.warning(
                "file_cache_read_error",
                path=resolved_path,
                error=str(exc),
            )
            return None

    def get(self, file_path: str) -> CachedFile | None:
        """Get cached file entry (synchronous, no disk read)."""
        resolved_path = str(Path(file_path).resolve())
        cached = self._cache.get(resolved_path)

        if cached and not cached.is_expired(self.ttl_seconds):
            cached.touch()
            self._update_access_order(resolved_path)
            self._stats["hits"] += 1
            return cached

        return None

    def put(self, file_path: str, content: str) -> CachedFile:
        """Manually add a file to the cache."""
        resolved_path = str(Path(file_path).resolve())

        try:
            stat = os.stat(resolved_path)
            mtime = stat.st_mtime
            size = stat.st_size
        except OSError:
            mtime = time.time()
            size = len(content.encode("utf-8"))

        cached = CachedFile(
            path=resolved_path,
            content=content,
            content_hash=self._compute_hash(content),
            mtime=mtime,
            size=size,
            token_estimate=self._estimate_tokens(content),
        )

        content_bytes = len(content.encode("utf-8"))
        self._evict_lru(content_bytes)

        self._cache[resolved_path] = cached
        self._update_access_order(resolved_path)
        self._stats["bytes_cached"] += content_bytes

        return cached

    def invalidate(self, file_path: str) -> bool:
        """Invalidate a cached file entry."""
        resolved_path = str(Path(file_path).resolve())

        if resolved_path in self._cache:
            evicted = self._cache.pop(resolved_path)
            self._stats["invalidations"] += 1
            self._stats["bytes_cached"] -= len(evicted.content.encode("utf-8"))

            if resolved_path in self._access_order:
                self._access_order.remove(resolved_path)

            logger.debug("file_cache_invalidated_manual", path=resolved_path)
            return True

        return False

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._access_order.clear()
        self._stats["bytes_cached"] = 0
        logger.info("file_cache_cleared", session_id=self.session_id)

    def get_recent_files(
        self,
        max_files: int = 10,
        max_tokens: int = 50_000,
    ) -> list[CachedFile]:
        """Get most recently accessed files (for post-compact restoration).

        Args:
            max_files: Maximum number of files to return.
            max_tokens: Maximum total token budget.

        Returns:
            List of CachedFile entries, sorted by recency.
        """
        sorted_files = sorted(
            self._cache.values(),
            key=lambda f: f.last_accessed,
            reverse=True,
        )

        result = []
        total_tokens = 0

        for cached in sorted_files[:max_files]:
            if total_tokens + cached.token_estimate > max_tokens:
                break
            result.append(cached)
            total_tokens += cached.token_estimate

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        hit_rate = 0.0
        total = self._stats["hits"] + self._stats["misses"]
        if total > 0:
            hit_rate = self._stats["hits"] / total

        return {
            "session_id": self.session_id,
            "entries": len(self._cache),
            "bytes_cached": self._stats["bytes_cached"],
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate, 3),
            "evictions": self._stats["evictions"],
            "invalidations": self._stats["invalidations"],
        }

    def save(self) -> None:
        """Persist cache to disk."""
        try:
            data = {
                "session_id": self.session_id,
                "version": 1,
                "created_at": time.time(),
                "entries": {
                    path: cached.to_dict()
                    for path, cached in self._cache.items()
                },
                "stats": self._stats,
            }

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(
                "file_cache_saved",
                path=str(self.cache_file),
                entries=len(self._cache),
            )
        except Exception as exc:
            logger.warning(
                "file_cache_save_error",
                error=str(exc),
                path=str(self.cache_file),
            )

    def load(self) -> bool:
        """Load cache from disk.

        Returns:
            True if cache was loaded successfully.
        """
        if not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            # Validate version
            if data.get("version") != 1:
                logger.warning(
                    "file_cache_version_mismatch",
                    expected=1,
                    got=data.get("version"),
                )
                return False

            # Load entries
            for path, entry_data in data.get("entries", {}).items():
                try:
                    cached = CachedFile.from_dict(entry_data)
                    self._cache[path] = cached
                    self._access_order.append(path)
                except Exception as exc:
                    logger.debug(
                        "file_cache_entry_load_error",
                        path=path,
                        error=str(exc),
                    )

            # Load stats
            if "stats" in data:
                self._stats.update(data["stats"])

            logger.info(
                "file_cache_loaded",
                session_id=self.session_id,
                entries=len(self._cache),
            )
            return True

        except Exception as exc:
            logger.warning(
                "file_cache_load_error",
                error=str(exc),
                path=str(self.cache_file),
            )
            return False


def create_session_cache(
    session_id: str,
    cache_dir: str | None = None,
    **kwargs: Any,
) -> SessionFileCache:
    """Create a session file cache with optional disk persistence.

    Args:
        session_id: Unique session identifier.
        cache_dir: Cache directory (default: ~/.mindflow/cache/file_cache).
        **kwargs: Additional arguments for SessionFileCache.

    Returns:
        SessionFileCache instance.
    """
    cache = SessionFileCache(
        session_id=session_id,
        cache_dir=cache_dir,
        **kwargs,
    )

    # Try to load existing cache
    cache.load()

    return cache