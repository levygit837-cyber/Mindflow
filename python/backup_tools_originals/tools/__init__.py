"""Enhanced tool system for MindFlow agents.

Provides modular, extensible tool architecture with:
- Abstract interfaces for consistent tool behavior
- Enhanced registry with granular permissions
- Comprehensive validation and error handling
- Auto-discovery and caching capabilities
- Backward compatibility with existing tools
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, Optional, List, Dict

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

# Import new registry
from .base.tool_registry import ToolRegistry
from .base.tool_schemas import ToolSchema

# Import tool modules for auto-discovery
from . import filesystem, web, system, code, research
from . import ai, data, integration

# Legacy imports for backward compatibility
from .web.browser_search import BrowserSearchTool, get_browser_search_tool
from .system.sandbox import MindFlowSandbox, get_sandbox_tool

__all__ = [
    # Core components
    "ToolRegistry",
    "ToolSchema",
    
    # Tool modules
    "filesystem",
    "web", 
    "system",
    "code",
    "research",
    "ai",
    "data",
    "integration",
    
    # Legacy compatibility
    "BrowserSearchTool",
    "get_browser_search_tool",
    "MindFlowSandbox", 
    "get_sandbox_tool",
]
