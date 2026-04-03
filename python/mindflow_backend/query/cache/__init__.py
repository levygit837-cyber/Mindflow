"""Query cache module for MindFlow backend.

Provides caching utilities for query execution:
- SessionFileCache: Persistent file state cache across turns
- SystemContextCache: Reduces API cost with prompt caching
- GitStatusCache: Memoized git status operations
- FileDiscoveryCache: Cached file discovery results
- Memoization decorators for expensive operations
"""

from mindflow_backend.query.cache.file_cache import (
    CachedFile,
    SessionFileCache,
    create_session_cache,
)
from mindflow_backend.query.cache.memoization import (
    MemoizedResult,
    clear_all_caches,
    clear_all_file_caches,
    clear_all_git_caches,
    get_memoization_stats,
    memoize_file_discovery,
    memoize_git,
)
from mindflow_backend.query.cache.system_context_cache import (
    CachedContext,
    SystemContextCache,
    create_system_context_cache,
)

__all__ = [
    # File cache
    "CachedFile",
    "SessionFileCache",
    "create_session_cache",
    # System context cache
    "CachedContext",
    "SystemContextCache",
    "create_system_context_cache",
    # Memoization
    "MemoizedResult",
    "memoize_git",
    "memoize_file_discovery",
    "clear_all_git_caches",
    "clear_all_file_caches",
    "clear_all_caches",
    "get_memoization_stats",
]
