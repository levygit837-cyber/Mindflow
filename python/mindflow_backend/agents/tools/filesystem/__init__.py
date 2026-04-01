"""Filesystem tools for MindFlow agents.

Provides tools for file operations, directory management,
and file system interactions with proper validation and
error handling.
"""

from __future__ import annotations

# File operations v3 (New Tool system - migrated)
from .file_operations_v3 import (
    FileReadToolV3,
)
from .file_write_v3 import (
    FileWriteToolV3,
)
from .file_edit_v3 import (
    FileEditToolV3,
)
from .grep_v3 import (
    GrepToolV3,
)
from .glob_v3 import (
    GlobToolV3,
)

# Directory and file management v3 (New Tool system - Phase 1 migration)
from .directory_list_v3 import (
    DirectoryListToolV3,
)
from .directory_create_v3 import (
    DirectoryCreateToolV3,
)
from .file_delete_v3 import (
    FileDeleteToolV3,
)
from .file_finder_v3 import (
    FileFinderToolV3,
    FindFilesToolV3,
)

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
    # File operations v3 (New Tool system - migrated)
    "FileReadToolV3",
    "FileWriteToolV3",
    "FileEditToolV3",
    "GrepToolV3",
    "GlobToolV3",

    # Directory and file management v3 (Phase 1 migration)
    "DirectoryListToolV3",
    "DirectoryCreateToolV3",
    "FileDeleteToolV3",
    "FileFinderToolV3",
    "FindFilesToolV3",

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
