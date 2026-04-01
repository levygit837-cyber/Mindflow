"""System tools for MindFlow agents.

Provides tools for system interactions including sandbox execution,
process management, and environment access.
"""

from __future__ import annotations

# System tools v3 (New Tool system - Phase 2 migration)
from .system_info_v3 import (
    SystemInfoToolV3,
)
from .process_manager_v3 import (
    ProcessManagerToolV3,
)
from .resource_monitor_v3 import (
    ResourceMonitorToolV3,
)

# Shell executor v3 (New Tool system - migrated)
from .shell_executor_v3 import (
    ShellExecutorToolV3,
)

# Shell executor v2 (Claude Code standard)
# Temporarily commented out due to import error
# from .shell_executor_v2 import (
#     ShellExecutorToolV2,
# )

# Shell executor v1 (backward compatibility - deprecated)
from .shell_executor import (
    ShellExecutorTool,
)

# Original system tools
from ..sandbox import MindFlowSandbox  # Import from parent directory
from .process_manager import ProcessManagerTool
from .resource_monitor import (
    ResourceMonitorTool,
)
from .system_info import (
    SystemInfoTool,
)

from .shell_tabs import (
    ShellTabCloseTool,
    ShellTabExecTool,
    ShellTabListTool,
    ShellTabOpenTool,
    ShellTabReadTool,
    ShellTabStatusTool,
)

__all__ = [
    # System tools v3 (Phase 2 migration)
    "SystemInfoToolV3",
    "ProcessManagerToolV3",
    "ResourceMonitorToolV3",

    # Shell executor v3 (New Tool system - migrated)
    "ShellExecutorToolV3",

    # Shell executor v2 (default)
    # "ShellExecutorToolV2",  # Temporarily commented out

    # Shell executor v1 (deprecated)
    "ShellExecutorTool",

    # Other system tools (v1 - backward compatibility)
    "ResourceMonitorTool",
    "SystemInfoTool",
    "ProcessManagerTool",
    "ShellTabOpenTool",
    "ShellTabListTool",
    "ShellTabStatusTool",
    "ShellTabExecTool",
    "ShellTabReadTool",
    "ShellTabCloseTool",

    # Original system tools
    "MindFlowSandbox",
]
