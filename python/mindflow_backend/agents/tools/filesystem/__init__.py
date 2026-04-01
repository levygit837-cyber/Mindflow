"""Filesystem tools for MindFlow agents.

Provides tools for file operations, directory management,
and file system interactions with proper validation and
error handling.
"""

from __future__ import annotations

# File operations v2 (Claude Code standard)
from .file_operations_v2 import (
    FileEditToolV2,
    FileReadToolV2,
    FileWriteToolV2,
)

# Search tools v2 (Claude Code standard)
from .search_tools_v2 import (
    GlobToolV2,
    GrepToolV2,
)

# File operations v1 (backward compatibility - deprecated)
from .file_operations import (
    FileEditTool,
    FileReadTool,
    FileWriteTool,
)

# Original tools (backward compatibility)
from .operations import (
    DirectoryCreateTool,
    DirectoryListTool,
    FileDeleteTool,
)

# Search tools v1 (backward compatibility - deprecated)
from .search_tools import (
    FindFilesTool,
    GlobSearchTool,
    GrepSearchTool,
)

__all__ = [
    # File operations v2 (default)
    "FileReadToolV2",
    "FileWriteToolV2",
    "FileEditToolV2",

    # Search tools v2 (default)
    "GrepToolV2",
    "GlobToolV2",

    # File operations v1 (deprecated)
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",

    # Search tools v1 (deprecated)
    "GrepSearchTool",
    "GlobSearchTool",
    "FindFilesTool",

    # Original tools (backward compatibility)
    "DirectoryListTool",
    "FileDeleteTool",
    "DirectoryCreateTool",
]
