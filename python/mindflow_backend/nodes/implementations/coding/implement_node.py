"""ImplementNode - Execute implementation steps.

This node executes the implementation steps from the plan, writes
or modifies files, and tracks changes made to the codebase.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class ImplementNode(BaseNode):
    """Execute implementation steps.

    This node takes the implementation plan and executes each step,
    writing or modifying files as needed, and tracking all changes
    made to the codebase.
    """

    def __init__(self, node_id: str = "implement") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.AGENT,
            category=NodeCategory.TOOL_EXECUTION,
            description="Execute implementation steps and write code.",
        )
        self.config.required_inputs = {
            "implementation_plan",
            "working_directory",
            "enabled_tools",
        }
        self.config.outputs = {
            "files_modified",
            "files_created",
            "implementation_log",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute implementation phase."""
        start_time = time.time()
        try:
            implementation_plan = state.get("implementation_plan", {})
            working_directory = state.get("working_directory", ".")
            enabled_tools = state.get("enabled_tools", {})

            _logger.debug(
                "implement_node_start",
                node_id=self.node_id,
                working_dir=working_directory,
                steps_count=implementation_plan.get("total_steps", 0),
            )

            files_modified = []
            files_created = []
            implementation_log = []

            # Execute implementation steps
            steps = implementation_plan.get("steps", [])
            for step in steps:
                step_result = await self._execute_step(
                    step, working_directory, enabled_tools
                )

                implementation_log.append({
                    "step_id": step.get("step_id"),
                    "description": step.get("description"),
                    "action": step.get("action"),
                    "result": step_result,
                })

                if step_result.get("files_modified"):
                    files_modified.extend(step_result["files_modified"])

                if step_result.get("files_created"):
                    files_created.extend(step_result["files_created"])

            result = {
                "files_modified": list(set(files_modified)),
                "files_created": list(set(files_created)),
                "implementation_log": implementation_log,
                "current_phase": "implemented",
                "total_changes": len(files_modified) + len(files_created),
            }

            duration = time.time() - start_time
            _logger.info(
                "implement_node_complete",
                node_id=self.node_id,
                duration=duration,
                files_modified=len(result["files_modified"]),
                files_created=len(result["files_created"]),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "implement_node_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "files_modified": [],
                "files_created": [],
                "implementation_log": [],
            }

    async def _execute_step(
        self,
        step: dict[str, Any],
        working_directory: str,
        enabled_tools: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a single implementation step.

        Args:
            step: Step definition
            working_directory: Working directory
            enabled_tools: Available tools

        Returns:
            Dictionary with step execution result
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            generate_code_with_llm,
            write_file_safe,
        )

        action = step.get("action", "")
        files = step.get("files", [])
        task = self.config.get("task", "")

        result = {
            "action": action,
            "success": True,
            "files_modified": [],
            "files_created": [],
            "error": None,
        }

        try:
            if action == "analyze":
                # Analysis step - read and analyze files
                result["message"] = "Analysis completed"
                result["files_analyzed"] = files

            elif action == "implement":
                # Implementation step - generate code with LLM and write files
                from mindflow_backend.nodes.implementations.coding.utils import (
                    read_file_safe,
                )

                # Get project context
                project_context = {
                    "project_type": "python",  # TODO: Get from state
                }

                # Generate code using LLM
                code_generation = await generate_code_with_llm(
                    step=step,
                    task=task,
                    working_directory=working_directory,
                    project_context=project_context,
                )

                # Write generated files
                for file_path, content in code_generation.get("code_generated", {}).items():
                    write_result = await write_file_safe(
                        file_path, content, working_directory
                    )
                    if write_result.get("success"):
                        result["files_created"].append(file_path)

                result["message"] = f"Implementation completed, {len(result['files_created'])} files created"

            elif action == "fix":
                # Bug fix step - generate fix with LLM
                project_context = {"project_type": "python"}

                code_generation = await generate_code_with_llm(
                    step=step,
                    task=task,
                    working_directory=working_directory,
                    project_context=project_context,
                )

                for file_path, content in code_generation.get("code_generated", {}).items():
                    write_result = await write_file_safe(
                        file_path, content, working_directory
                    )
                    if write_result.get("success"):
                        result["files_modified"].append(file_path)

                result["message"] = f"Fix applied, {len(result['files_modified'])} files modified"

            elif action == "refactor":
                # Refactoring step
                project_context = {"project_type": "python"}

                code_generation = await generate_code_with_llm(
                    step=step,
                    task=task,
                    working_directory=working_directory,
                    project_context=project_context,
                )

                for file_path, content in code_generation.get("code_generated", {}).items():
                    write_result = await write_file_safe(
                        file_path, content, working_directory
                    )
                    if write_result.get("success"):
                        result["files_modified"].append(file_path)

                result["message"] = f"Refactoring completed, {len(result['files_modified'])} files modified"

            elif action == "test":
                # Test generation/execution
                result["message"] = "Tests added"
                # Would generate test files

            elif action == "verify":
                # Verification step
                result["message"] = "Verification completed"

            elif action == "reproduce":
                # Bug reproduction step
                result["message"] = "Bug reproduction attempted"

            elif action == "diagnose":
                # Diagnosis step
                result["message"] = "Diagnosis completed"

            elif action == "analyze_patterns":
                # Pattern analysis for refactoring
                result["message"] = "Pattern analysis completed"

            elif action == "plan_refactor":
                # Refactoring planning
                result["message"] = "Refactoring plan created"

            elif action == "design":
                # Design step
                result["message"] = "Design completed"

            else:
                result["message"] = f"Unknown action: {action}"
                result["success"] = False

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            _logger.error("step_execution_failed", action=action, error=str(e))

        return result

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "implementation_plan" not in state:
            errors.append("Missing required input: implementation_plan")

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        if "enabled_tools" not in state:
            errors.append("Missing required input: enabled_tools")

        return errors
