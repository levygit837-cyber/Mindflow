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

# Shell executor v2 (Claude Code standard)
from .shell_executor_v2 import (
    ShellExecutorToolV2,
)

# Shell executor v1 (backward compatibility - deprecated)
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
    # Shell executor v2 (default)
    "ShellExecutorToolV2",

    # Shell executor v1 (deprecated)
    "ShellExecutorTool",

    # Other system tools
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
