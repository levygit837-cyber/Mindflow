"""ReadContextNode - Generic node for reading project context.

This node scans the filesystem and maps project structure to provide
context for mission execution.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class ReadContextNode(BaseNode):
    """Read project context: filesystem scan, structure mapping.

    This node is reusable across all graphs and provides the necessary
    context about the project structure and relevant files.
    """

    def __init__(self, node_id: str = "read_context") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CUSTOM,
            category=NodeCategory.DATA_PROCESSING,
            description="Scan filesystem and map project structure.",
        )
        self.config.required_inputs = {"working_directory"}
        self.config.outputs = {
            "project_structure",
            "relevant_files",
            "file_count",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute context reading."""
        try:
            working_dir = state.get("working_directory", ".")

            _logger.debug(
                "read_context_node_start",
                node_id=self.node_id,
                working_dir=working_dir,
            )

            # Scan filesystem
            from mindflow_backend.nodes.common.utils import scan_filesystem

            project_structure = await scan_filesystem(working_dir)

            # Map project structure
            from mindflow_backend.nodes.common.utils import map_project_structure

            structure_map = map_project_structure(project_structure)

            # Identify relevant files based on mission type
            from mindflow_backend.nodes.common.utils import identify_relevant_files

            mission_type = state.get("mission_type", "analysis")
            relevant_files = identify_relevant_files(
                structure_map, mission_type, working_dir
            )

            result = {
                "project_structure": structure_map,
                "relevant_files": relevant_files,
                "file_count": len(project_structure.get("files", [])),
                "current_phase": "context_read",
            }

            _logger.debug(
                "read_context_node_complete",
                node_id=self.node_id,
                file_count=result["file_count"],
                relevant_files_count=len(relevant_files),
            )

            return result

        except Exception as e:
            _logger.error("read_context_node_failed", node_id=self.node_id, error=str(e))
            return {
                "project_structure": {},
                "relevant_files": [],
                "file_count": 0,
                "current_phase": "error",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        return errors
