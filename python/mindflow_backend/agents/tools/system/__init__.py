"""System tools for MindFlow agents.

Provides tools for system interactions including sandbox execution,
process management, and environment access.
"""

from __future__ import annotations

# Original system tools
from ..sandbox import MindFlowSandbox  # Import from parent directory
from .process_manager import ProcessManagerTool
from .resource_monitor import (
    ResourceMonitorTool,
)

# System tools (unified from backend)
from .shell_executor import (
    ShellExecutorTool,
)
from .shell_tabs import (
    ShellTabCloseTool,
    ShellTabExecTool,
    ShellTabListTool,
    ShellTabOpenTool,
    ShellTabReadTool,
    ShellTabStatusTool,
)
from .system_info import (
    SystemInfoTool,
)

__all__ = [
    # System tools (unified)
    "ShellExecutorTool",
    "ResourceMonitorTool",
    "SystemInfoTool",
    "ShellTabOpenTool",
    "ShellTabListTool",
    "ShellTabStatusTool",
    "ShellTabExecTool",
    "ShellTabReadTool",
    "ShellTabCloseTool",
    
    # Original system tools
    "MindFlowSandbox",
    "ProcessManagerTool",
]
