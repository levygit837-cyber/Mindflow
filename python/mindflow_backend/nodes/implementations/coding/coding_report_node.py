"""CodingReportNode - Generate coding task report.

This node compiles results from all nodes, generates a structured
report, annotates memory, and formats the final result for the user.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class CodingReportNode(BaseNode):
    """Generate coding task report.

    This node compiles the results from all execution nodes, generates
    a structured report, annotates the memory with key findings, and
    formats the final result for presentation to the user.
    """

    def __init__(self, node_id: str = "report") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CUSTOM,
            category=NodeCategory.DATA_PROCESSING,
            description="Generate coding task report with metrics and annotations.",
        )
        self.config.required_inputs = {
            "agent_id",
            "mission_type",
            "session_id",
        }
        self.config.outputs = {
            "final_result",
            "metrics",
            "annotations",
            "status",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute reporting phase."""
        start_time = time.time()
        try:
            agent_id = state.get("agent_id")
            mission_type = state.get("mission_type")
            session_id = state.get("session_id")

            _logger.debug(
                "coding_report_start",
                node_id=self.node_id,
                agent_id=agent_id,
                mission_type=mission_type,
            )

            # Compile metrics
            metrics = await self._compile_metrics(state)

            # Generate final result
            final_result = await self._generate_final_result(state)

            # Generate memory annotations
            annotations = await self._generate_memory_annotations(state, agent_id, mission_type, session_id)

            # Determine overall status
            status = await self._determine_status(state)

            result = {
                "final_result": final_result,
                "metrics": metrics,
                "annotations": annotations,
                "status": status,
                "current_phase": "completed",
            }

            duration = time.time() - start_time
            _logger.info(
                "coding_report_complete",
                node_id=self.node_id,
                duration=duration,
                status=status,
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "coding_report_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "status": "failed",
            }

    async def _compile_metrics(self, state: dict[str, Any]) -> dict[str, Any]:
        """Compile execution metrics from all nodes.

        Args:
            state: Current graph state

        Returns:
            Dictionary with compiled metrics
        """
        from mindflow_backend.nodes.common.utils import compile_metrics

        base_metrics = compile_metrics(state)

        # Add coding-specific metrics
        coding_metrics = {
            "files_modified": len(state.get("files_modified", [])),
            "files_created": len(state.get("files_created", [])),
            "verify_retries": state.get("verify_retries", 0),
            "auto_verify_passed": state.get("auto_verify_passed", False),
            "verify_passed": state.get("verify_passed", False),
            "tests_passed": state.get("tests_passed", 0),
            "tests_failed": state.get("tests_failed", 0),
            "lint_errors": len(state.get("lint_report", {}).get("errors", [])),
            "type_errors": len(state.get("type_check_report", {}).get("errors", [])),
        }

        base_metrics.update(coding_metrics)

        return base_metrics

    async def _generate_final_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate final result summary.

        Args:
            state: Current graph state

        Returns:
            Dictionary with final result
        """
        mission_type = state.get("mission_type", "unknown")
        verify_passed = state.get("verify_passed", False)
        tests_passed = state.get("tests_passed", 0)
        tests_failed = state.get("tests_failed", 0)

        result = {
            "mission_type": mission_type,
            "success": verify_passed and tests_failed == 0,
            "files_modified": state.get("files_modified", []),
            "files_created": state.get("files_created", []),
            "verification": {
                "auto_verify_passed": state.get("auto_verify_passed", False),
                "verify_passed": verify_passed,
                "verify_retries": state.get("verify_retries", 0),
            },
            "tests": {
                "passed": tests_passed,
                "failed": tests_failed,
                "skipped": state.get("tests_skipped", 0),
            },
            "quality": {
                "lint_errors": len(state.get("lint_report", {}).get("errors", [])),
                "type_errors": len(state.get("type_check_report", {}).get("errors", [])),
            },
            "coverage": state.get("coverage"),
        }

        # Add architectural notes if available
        architectural_notes = state.get("architectural_notes", {})
        if architectural_notes.get("notes"):
            result["architectural_notes"] = architectural_notes["notes"]

        return result

    async def _generate_memory_annotations(
        self, state: dict[str, Any], agent_id: str, mission_type: str, session_id: str
    ) -> list[dict[str, Any]]:
        """Generate memory annotations from mission results.

        Args:
            state: Current graph state
            agent_id: Agent identifier
            mission_type: Mission type
            session_id: Session identifier

        Returns:
            List of memory annotations
        """
        from mindflow_backend.nodes.common.utils import generate_memory_annotations

        # Generate base annotations
        annotations = await generate_memory_annotations(state, agent_id, mission_type, session_id)

        # Ensure annotations is a list
        if not isinstance(annotations, list):
            annotations = []

        # Add coding-specific annotations
        files_modified = state.get("files_modified", [])
        files_created = state.get("files_created", [])

        if files_modified:
            annotations.append({
                "content": f"Modified files: {', '.join(files_modified)}",
                "agent_id": agent_id,
                "mission_type": mission_type,
                "session_id": session_id,
                "type": "files_modified",
                "confidence": 1.0,
                "timestamp": time.time(),
            })

        if files_created:
            annotations.append({
                "content": f"Created files: {', '.join(files_created)}",
                "agent_id": agent_id,
                "mission_type": mission_type,
                "session_id": session_id,
                "type": "files_created",
                "confidence": 1.0,
                "timestamp": time.time(),
            })

        # Add architectural notes if any
        architectural_notes = state.get("architectural_notes", {}).get("notes", [])
        for note in architectural_notes:
            annotations.append({
                "content": f"Architectural note: {note.get('message', note)}",
                "agent_id": agent_id,
                "mission_type": mission_type,
                "session_id": session_id,
                "type": "architectural",
                "confidence": 0.8,
                "timestamp": time.time(),
            })

        return annotations

    async def _determine_status(self, state: dict[str, Any]) -> str:
        """Determine overall mission status.

        Args:
            state: Current graph state

        Returns:
            Status string (completed, partial, failed)
        """
        verify_passed = state.get("verify_passed", False)
        tests_failed = state.get("tests_failed", 0)

        if verify_passed and tests_failed == 0:
            return "completed"
        elif verify_passed and tests_failed > 0:
            return "partial"
        else:
            return "failed"

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
