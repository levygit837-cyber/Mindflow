"""Callable tools - Phase 2 migration.

This package contains tools migrated to the CallableTool pattern.
All tools here use:
- Pydantic input schemas
- CallableToolResult return type
- build_callable_tool() / build_readonly_tool() / build_destructive_tool() factories
- Direct callable interface (no LangChain wrapper needed)

Migration status tracked in README.md.
"""

# Filesystem tools (Priority 1 - Read-only) ✅ COMPLETE
from .filesystem import (
    FileReadCallable,
    DirectoryListCallable,
    FileFinderCallable,
    GrepSearchCallable,
    GlobSearchCallable,
)

# Filesystem tools (Priority 2 - Write) ✅ COMPLETE
from .filesystem import (
    FileWriteCallable,
    FileEditCallable,
    FileDeleteCallable,
    DirectoryCreateCallable,
)

# System tools (Priority 3) ✅ COMPLETE
from .shell import (
    ShellExecutorCallable,
    SystemInfoCallable,
    ProcessManagerCallable,
)

# Web tools (Priority 4) ✅ COMPLETE
from .web import (
    HttpClientCallable,
    WebScraperCallable,
    ApiClientCallable,
)

# Planning tools (Priority 5)
# from .planning import (
#     TodoListReadCallable,
#     TodoListWriteCallable,
#     TodoListFocusCallable,
# )

__all__ = [
    # Priority 1 - Read-only filesystem (COMPLETE)
    "FileReadCallable",
    "DirectoryListCallable",
    "FileFinderCallable",
    "GrepSearchCallable",
    "GlobSearchCallable",
    # Priority 2 - Write filesystem (COMPLETE)
    "FileWriteCallable",
    "FileEditCallable",
    "FileDeleteCallable",
    "DirectoryCreateCallable",
    # Priority 3 - System (COMPLETE)
    "ShellExecutorCallable",
    "SystemInfoCallable",
    "ProcessManagerCallable",
    # Priority 4 - Web (COMPLETE)
    "HttpClientCallable",
    "WebScraperCallable",
    "ApiClientCallable",
]

