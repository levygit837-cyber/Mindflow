"""InitializeNode - Generic node for execution context initialization.

This node initializes the execution context including tools, memory scope,
and metrics based on AgentRuntimePolicy.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class InitializeNode(BaseNode):
    """Initialize execution context: tools, memory scope, agent policy.

    This node is reusable across all graphs and sets up the foundation
    for mission execution based on the agent's runtime policy.
    """

    def __init__(self, node_id: str = "initialize") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CUSTOM,
            category=NodeCategory.INTERNAL,
            description="Setup tools, memory scope, and agent policy for execution.",
        )
        self.config.required_inputs = {"agent_id", "mission_type", "session_id"}
        self.config.outputs = {
            "iteration",
            "confidence",
            "annotations",
            "enabled_tools",
            "memory_scope",
            "metrics",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute initialization."""
        try:
            agent_id = state.get("agent_id")
            mission_type = state.get("mission_type")
            session_id = state.get("session_id")
            max_iterations = state.get("max_iterations", 500)
            max_duration = state.get("max_duration_seconds", 300.0)

            _logger.debug(
                "initialize_node_start",
                node_id=self.node_id,
                agent_id=agent_id,
                mission_type=mission_type,
            )

            # Setup tools from policy
            from mindflow_backend.nodes.common.utils import setup_tools_from_policy

            tools_config = await setup_tools_from_policy(agent_id, session_id)

            # Configure memory scope
            from mindflow_backend.nodes.common.utils import configure_memory_scope

            memory_scope = await configure_memory_scope(agent_id, mission_type, session_id)

            # Initialize metrics
            from mindflow_backend.nodes.common.utils import initialize_metrics

            metrics = initialize_metrics(max_iterations, max_duration)

            result = {
                "iteration": 0,
                "confidence": 0.0,
                "annotations": [],
                "enabled_tools": tools_config.get("enabled_tools", {}),
                "memory_scope": memory_scope,
                "metrics": metrics,
                "current_phase": "initialized",
                "sandbox_mode": tools_config.get("sandbox_mode", "none"),
            }

            if "error" in tools_config:
                result["error"] = tools_config["error"]

            _logger.debug(
                "initialize_node_complete",
                node_id=self.node_id,
                enabled_tools_count=len(tools_config.get("enabled_tools", {})),
            )

            return result

        except Exception as e:
            _logger.error("initialize_node_failed", node_id=self.node_id, error=str(e))
            return {
                "iteration": 0,
                "confidence": 0.0,
                "annotations": [],
                "enabled_tools": {},
                "memory_scope": {},
                "metrics": {},
                "current_phase": "error",
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
