"""ReportNode - Generic node for generating final reports.

This node formats the final result, compiles metrics, and generates
memory annotations for the mission.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class ReportNode(BaseNode):
    """Generate final analysis report.

    This node is reusable across all graphs and handles the final
    formatting of results, metric compilation, and memory annotation.
    """

    def __init__(self, node_id: str = "report") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.FORMATTER,
            category=NodeCategory.DATA_PROCESSING,
            description="Generate final report with metrics and annotations.",
        )
        self.config.required_inputs = {"agent_id", "mission_type", "session_id"}
        self.config.outputs = {
            "result",
            "metrics",
            "memory_annotations",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute report generation."""
        try:
            agent_id = state.get("agent_id")
            mission_type = state.get("mission_type")
            session_id = state.get("session_id")

            _logger.debug(
                "report_node_start",
                node_id=self.node_id,
                agent_id=agent_id,
                mission_type=mission_type,
            )

            # Format final result
            from mindflow_backend.nodes.common.utils import format_final_result

            formatted_result = format_final_result(state)

            # Compile metrics
            from mindflow_backend.nodes.common.utils import compile_metrics

            metrics = compile_metrics(state)

            # Generate memory annotations
            from mindflow_backend.nodes.common.utils import generate_memory_annotations

            memory_annotations = await generate_memory_annotations(
                state, agent_id, mission_type, session_id
            )

            result = {
                "result": formatted_result,
                "metrics": metrics,
                "memory_annotations": memory_annotations,
                "current_phase": "completed",
            }

            _logger.debug(
                "report_node_complete",
                node_id=self.node_id,
                annotations_count=len(memory_annotations),
            )

            return result

        except Exception as e:
            _logger.error("report_node_failed", node_id=self.node_id, error=str(e))
            return {
                "result": {},
                "metrics": {},
                "memory_annotations": [],
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
