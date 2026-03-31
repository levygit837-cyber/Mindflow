"""Stub nodes for analysis graphs (Fase 2A)."""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory

_logger = get_logger(__name__)


class AnalysisInitializeNode(BaseNode):
    """Initialize analysis context: tools, memory scope, agent policy."""

    def __init__(self, node_id: str = "initialize") -> None:
        super().__init__(
            node_id=node_id,
            name="Analysis Initialize",
            description="Setup tools, memory scope, and agent policy for analysis.",
            category=NodeCategory.INITIALIZATION,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("analysis_initialize_node", node_id=self.node_id)
        return {
            "iteration": 0,
            "confidence": 0.0,
            "annotations": [],
            "analyzed_files": {},
            "current_phase": "initialized",
        }


class ReadContextNode(BaseNode):
    """Read project context: filesystem scan, structure mapping."""

    def __init__(self, node_id: str = "read_context") -> None:
        super().__init__(
            node_id=node_id,
            name="Read Context",
            description="Scan filesystem and map project structure.",
            category=NodeCategory.DATA_COLLECTION,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("read_context_node", node_id=self.node_id)
        return {"current_phase": "context_read"}


class InvestigateNode(BaseNode):
    """Iterative investigation of codebase aspects."""

    def __init__(self, node_id: str = "investigate") -> None:
        super().__init__(
            node_id=node_id,
            name="Investigate",
            description="Investigate codebase aspects iteratively.",
            category=NodeCategory.ANALYSIS,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        iteration = state.get("iteration", 0) + 1
        _logger.debug("investigate_node", node_id=self.node_id, iteration=iteration)
        return {
            "iteration": iteration,
            "current_phase": "investigating",
        }


class AnnotateNode(BaseNode):
    """Annotate findings from investigation pass."""

    def __init__(self, node_id: str = "annotate") -> None:
        super().__init__(
            node_id=node_id,
            name="Annotate",
            description="Annotate findings from current investigation pass.",
            category=NodeCategory.ANALYSIS,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        iteration = state.get("iteration", 0)
        annotations = list(state.get("annotations", []))
        annotations.append(f"annotation_pass_{iteration}")
        confidence = min(state.get("confidence", 0.0) + 0.15, 1.0)
        _logger.debug("annotate_node", node_id=self.node_id, iteration=iteration, confidence=confidence)
        return {
            "annotations": annotations,
            "confidence": confidence,
            "current_phase": "annotated",
        }


class SynthesizeNode(BaseNode):
    """Synthesize all annotations into coherent analysis."""

    def __init__(self, node_id: str = "synthesize") -> None:
        super().__init__(
            node_id=node_id,
            name="Synthesize",
            description="Merge and synthesize all annotations into coherent analysis.",
            category=NodeCategory.SYNTHESIS,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("synthesize_node", node_id=self.node_id)
        return {"current_phase": "synthesized"}


class AnalysisReportNode(BaseNode):
    """Generate final analysis report."""

    def __init__(self, node_id: str = "report") -> None:
        super().__init__(
            node_id=node_id,
            name="Analysis Report",
            description="Generate final analysis report.",
            category=NodeCategory.REPORTING,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("analysis_report_node", node_id=self.node_id)
        return {
            "current_phase": "completed",
            "result": {
                "iterations": state.get("iteration", 0),
                "confidence": state.get("confidence", 0.0),
                "annotations_count": len(state.get("annotations", [])),
            },
        }
