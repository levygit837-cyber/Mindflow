"""Tools system for MindFlow backend.

Provides comprehensive tool management with filesystem,
system, web, AI, data, and integration capabilities.
"""

from __future__ import annotations

# Core components
from .core import (
    ToolRegistry,
    ToolExecutor,
    PermissionManager,
)

# Filesystem tools
from .filesystem import (
    FileReadTool,
    FileWriteTool,
    FileEditTool,
    GrepSearchTool,
    GlobSearchTool,
    FindFilesTool,
    DirectoryListTool,
    FileDeleteTool,
    DirectoryCreateTool,
)

# System tools
from .system import (
    ShellExecutorTool,
    ProcessManagerTool,
    SystemInfoCollector,
    ResourceMonitor,
)

# Web tools
from .web import (
    HttpClientTool,
    WebScraperTool,
    ApiClientTool,
)

# AI tools
from .ai import (
    LocalModelTool,
    EmbeddingTool,
)

# Data tools
from .data import (
    DatabaseTool,
    CSVProcessorTool,
)

# Integration tools
from .integration import (
    GitTool,
    DockerTool,
)

__all__ = [
    # Core components
    "ToolRegistry",
    "ToolExecutor",
    "PermissionManager",
    
    # Filesystem tools
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "GrepSearchTool",
    "GlobSearchTool",
    "FindFilesTool",
    "DirectoryListTool",
    "FileDeleteTool",
    "DirectoryCreateTool",
    
    # System tools
    "ShellExecutorTool",
    "ProcessManagerTool",
    "SystemInfoCollector",
    "ResourceMonitor",
    
    # Web tools
    "HttpClientTool",
    "WebScraperTool",
    "ApiClientTool",
    
    # AI tools
    "LocalModelTool",
    "EmbeddingTool",
    
    # Data tools
    "DatabaseTool",
    "CSVProcessorTool",
    
    # Integration tools
    "GitTool",
    "DockerTool",
]
