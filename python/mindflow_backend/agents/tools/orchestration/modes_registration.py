"""Modes and Personas tools registration with MindFlow ToolRegistry.

Auto-registration of Plan Mode, Accept Edits, and Auto Mode tools.
"""

from __future__ import annotations

from mindflow_backend.agents.tools.base.tool_registry import get_tool_registry
from mindflow_backend.agents.tools.orchestration.enter_plan_mode import EnterPlanModeTool
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

TOOL_REGISTRATIONS = [
    (EnterPlanModeTool, "modes"),
]


def register_modes_tools() -> int:
    """Register all Modes and Personas tools with the MindFlow ToolRegistry.

    Returns:
        Number of tools successfully registered.
    """
    registry = get_tool_registry()
    registered = 0

    for tool_class, category in TOOL_REGISTRATIONS:
        try:
            if registry.register_tool(tool_class, category=category):
                registered += 1
                _logger.info(f"Registered Modes tool: {tool_class.__name__}")
            else:
                _logger.warning(f"Tool {tool_class.__name__} already registered, skipping")
        except Exception as e:
            _logger.error(f"Failed to register {tool_class.__name__}: {e}")

    _logger.info(f"Modes integration: {registered}/{len(TOOL_REGISTRATIONS)} tools registered")
    return registered