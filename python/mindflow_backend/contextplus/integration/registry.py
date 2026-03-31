# Context+ tools registration with MindFlow ToolRegistry
# FEATURE: Integration - Auto-registration of Context+ tools

from __future__ import annotations

from mindflow_backend.agents.tools.base.tool_registry import get_tool_registry
from mindflow_backend.contextplus.tools.analysis.blast_radius import BlastRadiusTool
from mindflow_backend.contextplus.tools.discovery.context_tree import ContextTreeTool
from mindflow_backend.contextplus.tools.discovery.file_skeleton import FileSkeletonTool
from mindflow_backend.contextplus.tools.discovery.semantic_search import SemanticSearchTool
from mindflow_backend.contextplus.tools.memory import (
    CreateRelationTool,
    SearchMemoryGraphTool,
    UpsertMemoryNodeTool,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

TOOL_REGISTRATIONS = [
    (ContextTreeTool, "discovery"),
    (FileSkeletonTool, "discovery"),
    (SemanticSearchTool, "discovery"),
    (BlastRadiusTool, "analysis"),
    (UpsertMemoryNodeTool, "memory"),
    (CreateRelationTool, "memory"),
    (SearchMemoryGraphTool, "memory"),
]


def register_contextplus_tools() -> int:
    """Register all Context+ tools with the MindFlow ToolRegistry.

    Returns:
        Number of tools successfully registered.
    """
    registry = get_tool_registry()
    registered = 0

    for tool_class, category in TOOL_REGISTRATIONS:
        try:
            if registry.register_tool(tool_class, category=category):
                registered += 1
                _logger.info(f"Registered Context+ tool: {tool_class.__name__}")
            else:
                _logger.warning(f"Tool {tool_class.__name__} already registered, skipping")
        except Exception as e:
            _logger.error(f"Failed to register {tool_class.__name__}: {e}")

    _logger.info(f"Context+ integration: {registered}/{len(TOOL_REGISTRATIONS)} tools registered")
    return registered