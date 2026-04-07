"""VerifyNode - Complete verification including tests and P2P consultation.

This node performs comprehensive verification including full linting,
type checking, test execution, and P2P consultation with Analyst
for architectural questions.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class VerifyNode(BaseNode):
    """Complete verification: lint, typecheck, tests, P2P consultation.

    This node performs comprehensive verification after auto-verify,
    including full linting, type checking, test execution, and
    consultation with Analyst via P2P for architectural concerns.
    """

    def __init__(self, node_id: str = "verify") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.AGENT,
            category=NodeCategory.VALIDATION,
            description="Verify implementation: lint, typecheck, tests, P2P.",
        )
        self.config.required_inputs = {
            "files_modified",
            "files_created",
            "working_directory",
            "agent_id",
        }
        self.config.outputs = {
            "verify_passed",
            "verify_retries",
            "lint_report",
            "type_check_report",
            "architectural_notes",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute verification phase."""
        start_time = time.time()
        try:
            files_modified = state.get("files_modified", [])
            files_created = state.get("files_created", [])
            working_directory = state.get("working_directory", ".")
            agent_id = state.get("agent_id", "coder")

            # Increment retry counter
            verify_retries = state.get("verify_retries", 0) + 1

            all_files = list(set(files_modified + files_created))

            _logger.debug(
                "verify_node_start",
                node_id=self.node_id,
                agent_id=agent_id,
                files_count=len(all_files),
                working_dir=working_directory,
                retry=verify_retries,
            )

            # Full linting
            lint_report = await self._run_full_lint(all_files, working_directory)

            # Type checking
            type_check_report = await self._run_type_check(all_files, working_directory)

            # Architectural consultation (if needed)
            architectural_notes = await self._consult_architecture_if_needed(
                agent_id, all_files, state
            )

            # Determine if verification passed
            verify_passed = (
                lint_report["success"] and
                type_check_report["success"] and
                len(lint_report.get("errors", [])) == 0 and
                len(type_check_report.get("errors", [])) == 0
            )

            result = {
                "verify_passed": verify_passed,
                "verify_retries": verify_retries,
                "lint_report": lint_report,
                "type_check_report": type_check_report,
                "architectural_notes": architectural_notes,
                "current_phase": "verified" if verify_passed else "verify_failed",
            }

            duration = time.time() - start_time
            _logger.info(
                "verify_node_complete",
                node_id=self.node_id,
                duration=duration,
                passed=verify_passed,
                retry=verify_retries,
                lint_errors=len(lint_report.get("errors", [])),
                type_errors=len(type_check_report.get("errors", [])),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "verify_node_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "verify_passed": False,
                "verify_retries": state.get("verify_retries", 0) + 1,
            }

    async def _run_full_lint(
        self, files: list[str], working_directory: str
    ) -> dict[str, Any]:
        """Run full linting on files.

        Args:
            files: List of files to lint
            working_directory: Working directory

        Returns:
            Dictionary with linting report
        """
        from mindflow_backend.nodes.implementations.coding.utils import run_linter

        all_errors = []
        all_warnings = []
        success = True

        for file_path in files:
            lint_result = await run_linter(file_path, working_directory, fix=False)

            if not lint_result["success"]:
                success = False

            all_errors.extend(lint_result.get("errors", []))
            all_warnings.extend(lint_result.get("warnings", []))

        return {
            "success": success,
            "errors": all_errors,
            "warnings": all_warnings,
            "total_errors": len(all_errors),
            "total_warnings": len(all_warnings),
        }

    async def _run_type_check(
        self, files: list[str], working_directory: str
    ) -> dict[str, Any]:
        """Run type checking on files.

        Args:
            files: List of files to check
            working_directory: Working directory

        Returns:
            Dictionary with type check report
        """
        from mindflow_backend.nodes.implementations.coding.utils import run_type_checker

        all_errors = []
        success = True

        for file_path in files:
            type_result = await run_type_checker(file_path, working_directory)

            if not type_result["success"]:
                success = False

            all_errors.extend(type_result.get("errors", []))

        return {
            "success": success,
            "errors": all_errors,
            "total_errors": len(all_errors),
        }

    async def _consult_architecture_if_needed(
        self, agent_id: str, files: list[str], state: dict[str, Any]
    ) -> dict[str, Any]:
        """Consult Analyst for architectural questions if needed.

        Args:
            agent_id: Current agent ID
            files: Files being verified
            state: Current graph state

        Returns:
            Dictionary with architectural notes
        """
        notes = []

        # Check if there are architectural concerns
        # This would be more sophisticated in a real implementation
        # For now, check if we're creating new modules or changing structure

        try:
            # Check P2P availability
            from mindflow_backend.nodes.implementations.coding.utils import check_p2p_availability

            p2p_status = await check_p2p_availability(state)

            if not p2p_status["available"]:
                notes.append({
                    "type": "p2p_unavailable",
                    "message": p2p_status["reason"],
                })
                return {"notes": notes}

            # If we have many files or significant changes, consult Analyst
            if len(files) > 5:
                question = (
                    f"Verifying implementation with {len(files)} files changed. "
                    "Please verify architectural consistency."
                )

                from mindflow_backend.nodes.implementations.coding.utils import (
                    consult_analyst_architecture,
                )

                consultation = await consult_analyst_architecture(
                    agent_id, question, state, timeout=30.0
                )

                if consultation["success"]:
                    notes.append({
                        "type": "analyst_feedback",
                        "feedback": consultation["response"],
                    })
                else:
                    notes.append({
                        "type": "consultation_failed",
                        "reason": consultation["error"],
                    })

        except Exception as e:
            _logger.warning("architecture_consultation_failed", error=str(e))
            notes.append({
                "type": "consultation_error",
                "error": str(e),
            })

        return {"notes": notes}

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "files_modified" not in state and "files_created" not in state:
            errors.append("Missing required input: files_modified or files_created")

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        if "agent_id" not in state:
            errors.append("Missing required input: agent_id")

        return errors
