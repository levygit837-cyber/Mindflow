"""PlanNode - Decompose coding task into implementation steps.

This node analyzes the task, decomposes it into structured steps,
analyzes dependencies, and creates an implementation plan.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class PlanNode(BaseNode):
    """Decompose task into implementation steps.

    This node analyzes the coding task, breaks it down into structured
    implementation steps, identifies dependencies, and creates a detailed
    plan for the ImplementNode to follow.
    """

    def __init__(self, node_id: str = "plan") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.AGENT,
            category=NodeCategory.LLM_INVOKE,
            description="Decompose coding task into implementation steps.",
        )
        self.config.required_inputs = {
            "agent_id",
            "mission_type",
            "task",
            "working_directory",
        }
        self.config.outputs = {
            "implementation_steps",
            "dependencies",
            "relevant_files",
            "implementation_plan",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute planning phase."""
        start_time = time.time()
        try:
            agent_id = state.get("agent_id")
            mission_type = state.get("mission_type")
            task = state.get("task", "")
            working_directory = state.get("working_directory", ".")
            project_context = state.get("project_context", {})

            _logger.debug(
                "plan_node_start",
                node_id=self.node_id,
                agent_id=agent_id,
                mission_type=mission_type,
                task_preview=task[:100],
            )

            # Analyze dependencies
            dependencies = await self._analyze_dependencies(
                working_directory, project_context
            )

            # Identify relevant files
            relevant_files = await self._identify_relevant_files(
                task, working_directory, project_context
            )

            # Decompose task into steps
            implementation_steps = await self._decompose_task(
                task, mission_type, relevant_files
            )

            # Create implementation plan
            implementation_plan = await self._create_implementation_plan(
                task, implementation_steps, dependencies, relevant_files
            )

            result = {
                "implementation_steps": implementation_steps,
                "dependencies": dependencies,
                "relevant_files": relevant_files,
                "implementation_plan": implementation_plan,
                "current_phase": "planned",
            }

            duration = time.time() - start_time
            _logger.info(
                "plan_node_complete",
                node_id=self.node_id,
                duration=duration,
                steps_count=len(implementation_steps),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "plan_node_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "implementation_steps": [],
                "dependencies": {},
                "relevant_files": [],
            }

    async def _analyze_dependencies(
        self, working_directory: str, project_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze project dependencies.

        Args:
            working_directory: Working directory
            project_context: Project context from initialize

        Returns:
            Dictionary with dependency analysis
        """
        try:
            from pathlib import Path

            project_type = project_context.get("project_type", "unknown")
            dependencies = {
                "external": [],
                "internal": [],
                "conflicts": [],
                "missing": [],
            }

            # Check for Python dependencies
            if project_type == "python":
                requirements_files = [
                    "requirements.txt",
                    "pyproject.toml",
                    "setup.py",
                    "poetry.lock",
                ]

                for req_file in requirements_files:
                    req_path = Path(working_directory) / req_file
                    if req_path.exists():
                        content = req_path.read_text()
                        # Parse requirements (simplified)
                        for line in content.split("\n"):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                dependencies["external"].append(line)

            # Check for JavaScript dependencies
            elif project_type in ("typescript", "javascript"):
                package_json = Path(working_directory) / "package.json"
                if package_json.exists():
                    import json
                    content = json.loads(package_json.read_text())
                    deps = content.get("dependencies", {})
                    dev_deps = content.get("devDependencies", {})

                    dependencies["external"] = list(deps.keys()) + list(dev_deps.keys())

            _logger.debug(
                "dependencies_analyzed",
                external_count=len(dependencies["external"]),
            )

            return dependencies

        except Exception as e:
            _logger.warning("dependency_analysis_failed", error=str(e))
            return {
                "external": [],
                "internal": [],
                "conflicts": [],
                "missing": [],
                "error": str(e),
            }

    async def _identify_relevant_files(
        self, task: str, working_directory: str, project_context: dict[str, Any]
    ) -> list[str]:
        """Identify files relevant to the task.

        Args:
            task: Task description
            working_directory: Working directory
            project_context: Project context

        Returns:
            List of relevant file paths
        """
        try:
            from pathlib import Path

            project_type = project_context.get("project_type", "unknown")
            by_extension = project_context.get("by_extension", {})

            relevant_files = []

            # Determine relevant extensions based on project type
            if project_type == "python":
                relevant_exts = [".py"]
            elif project_type in ("typescript", "javascript"):
                relevant_exts = [".ts", ".tsx", ".js", ".jsx"]
            else:
                relevant_exts = list(by_extension.keys())

            # Collect relevant files
            for ext in relevant_exts:
                if ext in by_extension:
                    relevant_files.extend(by_extension[ext])

            # Limit to top 50 most relevant files
            relevant_files = relevant_files[:50]

            _logger.debug(
                "relevant_files_identified",
                count=len(relevant_files),
            )

            return relevant_files

        except Exception as e:
            _logger.warning("relevant_files_identification_failed", error=str(e))
            return []

    async def _decompose_task(
        self, task: str, mission_type: str, relevant_files: list[str]
    ) -> list[dict[str, Any]]:
        """Decompose task into implementation steps using LLM.

        Args:
            task: Task description
            mission_type: Type of mission
            relevant_files: Relevant files

        Returns:
            List of implementation steps
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            decompose_task_with_llm,
        )

        # Get project context from state
        project_context = {
            "project_type": "python",  # TODO: Get from state
            "total_files": len(relevant_files),
        }

        # Use LLM to decompose task
        steps = await decompose_task_with_llm(
            task=task,
            mission_type=mission_type,
            relevant_files=relevant_files,
            project_context=project_context,
        )

        return steps

    async def _create_implementation_plan(
        self,
        task: str,
        steps: list[dict[str, Any]],
        dependencies: dict[str, Any],
        relevant_files: list[str],
    ) -> dict[str, Any]:
        """Create structured implementation plan.

        Args:
            task: Task description
            steps: Implementation steps
            dependencies: Dependency analysis
            relevant_files: Relevant files

        Returns:
            Dictionary with implementation plan
        """
        return {
            "task": task,
            "total_steps": len(steps),
            "steps": steps,
            "dependencies": dependencies,
            "affected_files": relevant_files,
            "estimated_complexity": len(steps) * len(relevant_files) / 10,
        }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "agent_id" not in state:
            errors.append("Missing required input: agent_id")

        if "mission_type" not in state:
            errors.append("Missing required input: mission_type")

        if "task" not in state:
            errors.append("Missing required input: task")

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        return errors
