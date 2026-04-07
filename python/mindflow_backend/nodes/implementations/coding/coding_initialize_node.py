"""CodingInitializeNode - Initialize coding context.

This node sets up the execution context for coding tasks including
sandbox configuration, tools loading, and memory scope setup.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class CodingInitializeNode(BaseNode):
    """Initialize coding context: sandbox, tools, memory read.

    This node sets up the foundation for coding task execution based on
    the agent's runtime policy, including sandbox configuration, tool loading,
    and memory scope setup.
    """

    def __init__(self, node_id: str = "initialize") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CUSTOM,
            category=NodeCategory.INTERNAL,
            description="Setup sandbox, tools, and memory for coding task.",
        )
        self.config.required_inputs = {"agent_id", "mission_type", "session_id"}
        self.config.outputs = {
            "enabled_tools",
            "sandbox_mode",
            "memory_scope",
            "metrics",
            "project_context",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute initialization for coding task."""
        start_time = time.time()
        try:
            agent_id = state.get("agent_id")
            mission_type = state.get("mission_type")
            session_id = state.get("session_id")
            working_directory = state.get("working_directory", ".")
            max_iterations = state.get("max_iterations", 1000)
            max_duration = state.get("max_duration_seconds", 300.0)

            _logger.debug(
                "coding_initialize_start",
                node_id=self.node_id,
                agent_id=agent_id,
                mission_type=mission_type,
                working_dir=working_directory,
            )

            # Setup tools from policy
            from mindflow_backend.nodes.common.utils import setup_tools_from_policy

            tools_config = await setup_tools_from_policy(agent_id, session_id)

            # Configure memory scope for coding tasks
            from mindflow_backend.nodes.common.utils import configure_memory_scope

            memory_scope = await configure_memory_scope(
                agent_id, mission_type, session_id
            )

            # Initialize metrics
            from mindflow_backend.nodes.common.utils import initialize_metrics

            metrics = initialize_metrics(max_iterations, max_duration)

            # Read initial project context
            project_context = await self._read_project_context(working_directory)

            result = {
                "enabled_tools": tools_config.get("enabled_tools", {}),
                "tool_scopes": tools_config.get("tool_scopes", []),
                "sandbox_mode": tools_config.get("sandbox_mode", "none"),
                "memory_scope": memory_scope,
                "metrics": metrics,
                "project_context": project_context,
                "current_phase": "initialized",
                "working_directory": working_directory,
            }

            if "error" in tools_config:
                result["error"] = tools_config["error"]
                result["current_phase"] = "error"

            duration = time.time() - start_time
            _logger.info(
                "coding_initialize_complete",
                node_id=self.node_id,
                duration=duration,
                tools_count=len(tools_config.get("enabled_tools", {})),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "coding_initialize_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "enabled_tools": {},
                "sandbox_mode": "none",
            }

    async def _read_project_context(self, working_directory: str) -> dict[str, Any]:
        """Read initial project context.

        Args:
            working_directory: Working directory

        Returns:
            Dictionary with project context
        """
        try:
            from mindflow_backend.nodes.common.utils import scan_filesystem, map_project_structure

            # Scan filesystem
            filesystem_scan = await scan_filesystem(working_directory)

            # Map project structure
            structure_map = map_project_structure(filesystem_scan)

            return {
                "project_type": structure_map.get("project_type", "unknown"),
                "total_files": structure_map.get("total_files", 0),
                "by_extension": structure_map.get("by_extension", {}),
                "root": filesystem_scan.get("root", working_directory),
            }

        except Exception as e:
            _logger.warning("project_context_read_failed", error=str(e))
            return {
                "project_type": "unknown",
                "total_files": 0,
                "by_extension": {},
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "agent_id" not in state:
            errors.append("Missing required input: agent_id")

        if "mission_type" not in state:
            errors.append("Missing required input: mission_type")

        if "session_id" not in state:
            errors.append("Missing required input: session_id")

        return errors
