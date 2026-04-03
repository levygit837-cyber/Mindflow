"""Compatibility wrapper for the canonical system information tool."""

from mindflow_backend.agents.tools.system.system_info import SystemInfoTool

SystemInfoCollector = SystemInfoTool

__all__ = ["SystemInfoTool", "SystemInfoCollector"]
