"""SynthesizeNode - Domain-specific node for Analyst synthesis.

This node synthesizes all annotations into coherent analysis narrative.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class SynthesizeNode(BaseNode):
    """Synthesize all annotations into coherent analysis.

    This node is specific to the Analyst agent and merges annotations,
    identifies common themes, and generates a structured narrative.
    """

    def __init__(self, node_id: str = "synthesize") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CUSTOM,
            category=NodeCategory.DATA_PROCESSING,
            description="Merge and synthesize all annotations into coherent analysis.",
        )
        self.config.required_inputs = {"annotations", "confidence"}
        self.config.outputs = {
            "synthesis",
            "themes",
            "narrative",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute synthesis."""
        try:
            annotations = state.get("annotations", [])
            confidence = state.get("confidence", 0.0)

            _logger.debug(
                "synthesize_node_start",
                node_id=self.node_id,
                annotations_count=len(annotations),
                confidence=confidence,
            )

            # Merge annotations
            from mindflow_backend.nodes.analysis.utils import merge_annotations

            merged = await merge_annotations(annotations)

            # Identify common themes
            from mindflow_backend.nodes.analysis.utils import identify_common_themes

            themes = await identify_common_themes(merged["grouped"])

            # Generate structured narrative
            from mindflow_backend.nodes.analysis.utils import generate_structured_narrative

            narrative = await generate_structured_narrative(merged["grouped"], themes, confidence)

            result = {
                "synthesis": merged,
                "themes": themes,
                "narrative": narrative,
                "current_phase": "synthesized",
            }

            _logger.debug(
                "synthesize_node_complete",
                node_id=self.node_id,
                themes_count=len(themes),
                narrative_length=len(narrative),
            )

            return result

        except Exception as e:
            _logger.error("synthesize_node_failed", node_id=self.node_id, error=str(e))
            return {
                "synthesis": {},
                "themes": [],
                "narrative": "",
                "current_phase": "error",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "annotations" not in state:
            errors.append("Missing required input: annotations")

        if "confidence" not in state:
            errors.append("Missing required input: confidence")

        return errors
