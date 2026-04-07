"""AnnotateNode - Domain-specific node for Analyst annotation.

This node annotates findings from investigation with confidence scoring
and memory annotation.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class AnnotateNode(BaseNode):
    """Annotate findings from investigation pass with confidence scoring.

    This node is specific to the Analyst agent and handles the annotation
    of investigation findings with confidence calculation and memory storage.
    """

    def __init__(self, node_id: str = "annotate") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CUSTOM,
            category=NodeCategory.DATA_PROCESSING,
            description="Annotate findings from current investigation pass.",
        )
        self.config.required_inputs = {"findings", "agent_id", "mission_type", "session_id"}
        self.config.outputs = {
            "annotations",
            "confidence",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute annotation."""
        try:
            findings = state.get("findings", {})
            agent_id = state.get("agent_id", "analyst")
            mission_type = state.get("mission_type", "analysis")
            session_id = state.get("session_id")
            iteration = state.get("iteration", 0)
            previous_confidence = state.get("confidence", 0.0)
            existing_annotations = state.get("annotations", [])

            _logger.debug(
                "annotate_node_start",
                node_id=self.node_id,
                agent_id=agent_id,
                iteration=iteration,
            )

            # Extract key insights from findings
            from mindflow_backend.nodes.analysis.utils import extract_key_insights

            insights = await extract_key_insights(findings, iteration)

            # Calculate confidence score
            from mindflow_backend.nodes.analysis.utils import calculate_confidence_score

            new_confidence = await calculate_confidence_score(insights, previous_confidence)

            # Save insights as memory annotations
            from mindflow_backend.nodes.analysis.utils import save_memory_annotation

            new_annotations = []
            for insight in insights:
                annotation = await save_memory_annotation(
                    insight, agent_id, mission_type, session_id
                )
                new_annotations.append(annotation)

            # Merge with existing annotations
            all_annotations = existing_annotations + new_annotations

            result = {
                "annotations": all_annotations,
                "confidence": new_confidence,
                "current_phase": "annotated",
                "new_annotations_count": len(new_annotations),
            }

            _logger.debug(
                "annotate_node_complete",
                node_id=self.node_id,
                iteration=iteration,
                confidence=new_confidence,
                annotations_count=len(all_annotations),
            )

            return result

        except Exception as e:
            _logger.error("annotate_node_failed", node_id=self.node_id, error=str(e))
            return {
                "annotations": state.get("annotations", []),
                "confidence": state.get("confidence", 0.0),
                "current_phase": "error",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "findings" not in state:
            errors.append("Missing required input: findings")

        if "agent_id" not in state:
            errors.append("Missing required input: agent_id")

        if "mission_type" not in state:
            errors.append("Missing required input: mission_type")

        if "session_id" not in state:
            errors.append("Missing required input: session_id")

        return errors
