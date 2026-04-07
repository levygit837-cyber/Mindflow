"""AutoVerifyNode - Quick verification after implementation.

This node performs quick verification immediately after implementation,
including basic linting, syntax checking, and import validation.
It does NOT run full test suites (that's for VerifyNode).
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class AutoVerifyNode(BaseNode):
    """Quick verification after implementation: lint, syntax, imports.

    This node performs fast verification checks immediately after
    implementation to catch basic errors before running full tests.
    It focuses on syntax, linting, and import validation.
    """

    def __init__(self, node_id: str = "auto_verify") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.TOOL,
            category=NodeCategory.TOOL_EXECUTION,
            description="Quick lint and syntax check after implementation.",
        )
        self.config.required_inputs = {
            "files_modified",
            "files_created",
            "working_directory",
        }
        self.config.outputs = {
            "auto_verify_passed",
            "lint_errors",
            "type_errors",
            "quick_fixes",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute auto-verification phase."""
        start_time = time.time()
        try:
            files_modified = state.get("files_modified", [])
            files_created = state.get("files_created", [])
            working_directory = state.get("working_directory", ".")

            all_files = list(set(files_modified + files_created))

            _logger.debug(
                "auto_verify_node_start",
                node_id=self.node_id,
                files_count=len(all_files),
                working_dir=working_directory,
            )

            lint_errors = []
            type_errors = []
            quick_fixes = []
            all_passed = True

            # Check each file
            for file_path in all_files:
                file_result = await self._verify_file(file_path, working_directory)

                if not file_result["passed"]:
                    all_passed = False

                lint_errors.extend(file_result.get("lint_errors", []))
                type_errors.extend(file_result.get("type_errors", []))
                quick_fixes.extend(file_result.get("quick_fixes", []))

            result = {
                "auto_verify_passed": all_passed,
                "lint_errors": lint_errors,
                "type_errors": type_errors,
                "quick_fixes": quick_fixes,
                "files_checked": len(all_files),
                "current_phase": "auto_verified",
            }

            duration = time.time() - start_time
            _logger.info(
                "auto_verify_node_complete",
                node_id=self.node_id,
                duration=duration,
                passed=all_passed,
                lint_errors_count=len(lint_errors),
                type_errors_count=len(type_errors),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "auto_verify_node_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "auto_verify_passed": False,
                "lint_errors": [],
                "type_errors": [],
            }

    async def _verify_file(self, file_path: str, working_directory: str) -> dict[str, Any]:
        """Verify a single file.

        Args:
            file_path: Path to the file
            working_directory: Working directory

        Returns:
            Dictionary with verification result
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            detect_language,
            quick_lint_check,
            validate_syntax,
        )

        result = {
            "file_path": file_path,
            "passed": True,
            "lint_errors": [],
            "type_errors": [],
            "quick_fixes": [],
        }

        try:
            # Read file content
            from mindflow_backend.nodes.implementations.coding.utils import read_file_safe
            content = await read_file_safe(file_path, working_directory)

            if content is None:
                result["passed"] = False
                result["lint_errors"].append({
                    "file": file_path,
                    "error": "Could not read file",
                })
                return result

            # Validate syntax
            language = await detect_language(file_path)
            syntax_result = await validate_syntax(content, language)

            if not syntax_result["valid"]:
                result["passed"] = False
                for syntax_error in syntax_result.get("errors", []):
                    result["lint_errors"].append({
                        "file": file_path,
                        "line": syntax_error.get("line", 0),
                        "error": syntax_error.get("message", "Syntax error"),
                    })

            # Quick lint check
            lint_result = await quick_lint_check(file_path, working_directory)

            if not lint_result["success"] or lint_result.get("style_errors"):
                result["passed"] = False
                for style_error in lint_result.get("style_errors", []):
                    result["lint_errors"].append({
                        "file": file_path,
                        "line": style_error.get("line", 0),
                        "code": style_error.get("code", "unknown"),
                        "message": style_error.get("message", "Style error"),
                    })

                # Suggest quick fixes
                for style_error in lint_result.get("style_errors", []):
                    if style_error.get("code") in ["E501", "W291", "W292"]:
                        result["quick_fixes"].append({
                            "file": file_path,
                            "line": style_error.get("line", 0),
                            "fix": "Auto-fix available",
                        })

            _logger.debug(
                "file_verified",
                file=file_path,
                passed=result["passed"],
            )

        except Exception as e:
            result["passed"] = False
            result["lint_errors"].append({
                "file": file_path,
                "error": str(e),
            })
            _logger.error("file_verification_failed", file=file_path, error=str(e))

        return result

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "files_modified" not in state and "files_created" not in state:
            errors.append("Missing required input: files_modified or files_created")

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        return errors
