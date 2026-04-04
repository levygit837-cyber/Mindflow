"""System tools for MindFlow agents."""

from __future__ import annotations

import warnings
from importlib import import_module

from ..sandbox import MindFlowSandbox
from .process_manager import ProcessManagerTool
from .resource_monitor import ResourceMonitorTool
from .shell_executor import ShellExecutorTool
from .shell_tabs import (
    ShellTabCloseTool,
    ShellTabExecTool,
    ShellTabListTool,
    ShellTabOpenTool,
    ShellTabReadTool,
    ShellTabStatusTool,
)
from .system_info import SystemInfoTool

_COMPAT_EXPORTS = {
    "SystemInfoToolV3": (".system_info_v3", "SystemInfoToolV3"),
    "ProcessManagerToolV3": (".process_manager_v3", "ProcessManagerToolV3"),
    "ResourceMonitorToolV3": (".resource_monitor_v3", "ResourceMonitorToolV3"),
    "ShellExecutorToolV3": (".shell_executor_v3", "ShellExecutorToolV3"),
    "ShellExecutorToolV2": (".shell_executor_v2", "ShellExecutorToolV2"),
}

__all__ = [
    "ShellExecutorTool",
    "ResourceMonitorTool",
    "SystemInfoTool",
    "ProcessManagerTool",
    "ShellTabOpenTool",
    "ShellTabListTool",
    "ShellTabStatusTool",
    "ShellTabExecTool",
    "ShellTabReadTool",
    "ShellTabCloseTool",
    "MindFlowSandbox",
]


def __getattr__(name: str):
    if name not in _COMPAT_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _COMPAT_EXPORTS[name]
    warnings.warn(
        (
            f"{__name__}.{name} is a deprecated compatibility export. "
            f"Import {attr_name} from {__name__}{module_name} instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value
