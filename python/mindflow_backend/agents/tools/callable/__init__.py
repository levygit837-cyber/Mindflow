"""Callable tools - Phase 2 migration.

This package contains tools migrated to the CallableTool pattern.
All tools here use:
- Pydantic input schemas
- CallableToolResult return type
- build_callable_tool() / build_readonly_tool() / build_destructive_tool() factories
- Direct callable interface (no LangChain wrapper needed)

Migration status tracked in README.md.

## Usage

To register all callable tools with the central registry:

```python
from mindflow_backend.agents.tools.callable import register_all_callable_tools

# During application startup
register_all_callable_tools()
```
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

# Planning tools (Priority 5) ✅ COMPLETE
from .planning import (
    TodoListReadCallable,
    TodoListWriteCallable,
    TodoListFocusCallable,
)

# Registration
from .registration import (
    register_all_callable_tools,
    unregister_all_callable_tools,
)

# Scope mapping
from .scope_mapping import (
    get_callable_tools_for_scope,
    get_all_callable_tools,
    get_callable_tools_by_names,
)

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
    # Priority 5 - Planning (COMPLETE)
    "TodoListReadCallable",
    "TodoListWriteCallable",
    "TodoListFocusCallable",
    # Registration
    "register_all_callable_tools",
    "unregister_all_callable_tools",
    # Scope mapping
    "get_callable_tools_for_scope",
    "get_all_callable_tools",
    "get_callable_tools_by_names",
]

