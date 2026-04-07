"""InvestigateNode - Domain-specific node for Analyst investigation.

This node investigates codebase aspects using tools and LLM interpretation.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class InvestigateNode(BaseNode):
    """Investigate codebase aspects iteratively with tools and LLM.

    This node is specific to the Analyst agent and performs code analysis
    using filesystem tools and LLM interpretation.
    """

    def __init__(self, node_id: str = "investigate") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.AGENT,
            category=NodeCategory.LLM_INVOKE,
            description="Investigate codebase with tools and LLM interpretation.",
        )
        self.config.required_inputs = {"relevant_files", "working_directory"}
        self.config.outputs = {
            "findings",
            "patterns_found",
            "dependencies",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute investigation."""
        try:
            relevant_files = state.get("relevant_files", [])
            working_dir = state.get("working_directory", ".")
            agent_id = state.get("agent_id", "analyst")
            # Get symbol to trace from state or use default
            symbol_to_trace = state.get("symbol_to_trace", "BaseNode")

            _logger.debug(
                "investigate_node_start",
                node_id=self.node_id,
                agent_id=agent_id,
                files_count=len(relevant_files),
                symbol_to_trace=symbol_to_trace,
            )

            # Define common code patterns to search
            patterns = [
                r"class\s+\w+",  # Class definitions
                r"def\s+\w+",  # Function definitions
                r"import\s+",  # Import statements
                r"async\s+def",  # Async functions
            ]

            # 1. Scan code patterns (tool execution)
            from mindflow_backend.nodes.analysis.utils import scan_code_patterns

            patterns_found = await scan_code_patterns(relevant_files, patterns, working_dir)

            # 2. Trace symbol dependencies (tool execution)
            from mindflow_backend.nodes.analysis.utils import trace_symbol_dependencies

            dependencies = await trace_symbol_dependencies(symbol_to_trace, relevant_files, working_dir)

            # 3. Analyze file structure (tool execution)
            from mindflow_backend.nodes.analysis.utils import analyze_file_structure

            structure = await analyze_file_structure(relevant_files, working_dir)

            # 4. Interpret findings with LLM
            from mindflow_backend.nodes.analysis.utils import interpret_findings_with_llm

            interpretation = await interpret_findings_with_llm(
                patterns_found, dependencies, structure, agent_id
            )

            result = {
                "findings": interpretation,
                "patterns_found": patterns_found,
                "dependencies": dependencies,
                "structure": structure,
                "current_phase": "investigating",
            }

            _logger.debug(
                "investigate_node_complete",
                node_id=self.node_id,
                patterns_count=patterns_found.get("total_matches", 0),
                dependencies_count=len(dependencies.get("dependencies", [])),
            )

            return result

        except Exception as e:
            _logger.error("investigate_node_failed", node_id=self.node_id, error=str(e))
            return {
                "findings": {},
                "patterns_found": {},
                "dependencies": {},
                "structure": {},
                "current_phase": "error",
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "relevant_files" not in state:
            errors.append("Missing required input: relevant_files")

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        return errors
