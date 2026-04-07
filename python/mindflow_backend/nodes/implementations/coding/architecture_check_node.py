"""ArchitectureCheckNode - Verify architectural consistency with P2P.

This node verifies architectural consistency, detects pattern violations,
and consults the Analyst via P2P for architectural questions.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class ArchitectureCheckNode(BaseNode):
    """Verify architectural consistency with P2P consultation.

    This node checks for architectural violations, analyzes code patterns,
    and consults the Analyst agent via P2P when architectural questions
    arise during implementation.
    """

    def __init__(self, node_id: str = "architecture_check") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.AGENT,
            category=NodeCategory.TOOL_EXECUTION,
            description="Verify architectural consistency with P2P consultation.",
        )
        self.config.required_inputs = {
            "agent_id",
            "files_modified",
            "files_created",
            "working_directory",
        }
        self.config.outputs = {
            "arch_check_passed",
            "arch_violations",
            "analyst_feedback",
            "arch_notes",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute architectural check."""
        start_time = time.time()
        try:
            agent_id = state.get("agent_id", "coder")
            files_modified = state.get("files_modified", [])
            files_created = state.get("files_created", [])
            working_directory = state.get("working_directory", ".")

            all_files = list(set(files_modified + files_created))

            _logger.debug(
                "architecture_check_start",
                node_id=self.node_id,
                agent_id=agent_id,
                files_count=len(all_files),
                working_dir=working_directory,
            )

            # Check for architectural violations
            arch_violations = await self._check_architectural_violations(
                all_files, working_directory
            )

            # Consult Analyst if needed
            analyst_feedback = await self._consult_analyst_if_needed(
                agent_id, all_files, arch_violations, state
            )

            # Determine if check passed
            arch_check_passed = len(arch_violations) == 0

            # Generate architectural notes
            arch_notes = await self._generate_arch_notes(
                arch_violations, analyst_feedback
            )

            result = {
                "arch_check_passed": arch_check_passed,
                "arch_violations": arch_violations,
                "analyst_feedback": analyst_feedback,
                "arch_notes": arch_notes,
                "current_phase": "architecture_checked",
            }

            duration = time.time() - start_time
            _logger.info(
                "architecture_check_complete",
                node_id=self.node_id,
                duration=duration,
                passed=arch_check_passed,
                violations_count=len(arch_violations),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "architecture_check_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "arch_check_passed": False,
                "arch_violations": [],
                "analyst_feedback": None,
            }

    async def _check_architectural_violations(
        self, files: list[str], working_directory: str
    ) -> list[dict[str, Any]]:
        """Check for architectural violations.

        Args:
            files: Files to check
            working_directory: Working directory

        Returns:
            List of architectural violations
        """
        violations = []

        for file_path in files:
            file_violations = await self._check_file_architecture(file_path, working_directory)
            violations.extend(file_violations)

        return violations

    async def _check_file_architecture(
        self, file_path: str, working_directory: str
    ) -> list[dict[str, Any]]:
        """Check a single file for architectural violations.

        Args:
            file_path: File to check
            working_directory: Working directory

        Returns:
            List of violations for this file
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            detect_language,
            read_file_safe,
        )

        violations = []

        try:
            content = await read_file_safe(file_path, working_directory)
            if content is None:
                return violations

            language = await detect_language(file_path)

            # Check for common architectural issues
            if language == "python":
                violations.extend(await self._check_python_architecture(content, file_path))
            elif language in ("typescript", "javascript"):
                violations.extend(await self._check_js_architecture(content, file_path))

        except Exception as e:
            _logger.warning("file_arch_check_failed", file=file_path, error=str(e))

        return violations

    async def _check_python_architecture(
        self, content: str, file_path: str
    ) -> list[dict[str, Any]]:
        """Check Python file for architectural violations.

        Args:
            content: File content
            file_path: File path

        Returns:
            List of violations
        """
        violations = []
        import re

        # Check for circular imports by analyzing import patterns
        # Look for relative imports that could cause cycles
        relative_imports = re.findall(r"from \.\.+\s+import", content)
        if len(relative_imports) > 3:
            violations.append({
                "file": file_path,
                "type": "complex_relative_imports",
                "message": f"Many relative imports found ({len(relative_imports)}), may indicate circular dependencies",
                "severity": "medium",
            })

        # Check for too many imports (high coupling)
        import_count = content.count("import ")
        if import_count > 30:
            violations.append({
                "file": file_path,
                "type": "high_coupling",
                "message": f"Too many imports ({import_count}), consider refactoring into modules",
                "severity": "medium",
            })

        # Check for large classes (god object anti-pattern)
        class_blocks = re.findall(r"class\s+\w+.*:(?:\n\s{4}.*?)+", content, re.MULTILINE | re.DOTALL)
        for class_block in class_blocks:
            if class_block.count("\n") > 100:  # More than 100 lines
                class_name = re.search(r"class\s+(\w+)", class_block)
                if class_name:
                    violations.append({
                        "file": file_path,
                        "type": "large_class",
                        "message": f"Class {class_name.group(1)} is too large ({class_block.count('\n')} lines), consider splitting",
                        "severity": "low",
                    })

        # Check for god function anti-pattern
        func_blocks = re.findall(r"def\s+\w+.*:(?:\n\s{4}.*?)+", content, re.MULTILINE | re.DOTALL)
        for func_block in func_blocks:
            if func_block.count("\n") > 50:  # More than 50 lines
                func_name = re.search(r"def\s+(\w+)", func_block)
                if func_name:
                    violations.append({
                        "file": file_path,
                        "type": "large_function",
                        "message": f"Function {func_name.group(1)} is too long ({func_block.count('\n')} lines), consider breaking down",
                        "severity": "low",
                    })

        return violations

    async def _check_js_architecture(
        self, content: str, file_path: str
    ) -> list[dict[str, Any]]:
        """Check JavaScript/TypeScript file for architectural violations.

        Args:
            content: File content
            file_path: File path

        Returns:
            List of violations
        """
        violations = []

        # Check for deep nesting
        max_nesting = 0
        current_nesting = 0
        for char in content:
            if char == "{":
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif char == "}":
                current_nesting -= 1

        if max_nesting > 5:
            violations.append({
                "file": file_path,
                "type": "deep_nesting",
                "message": f"Deep nesting detected (max: {max_nesting})",
                "severity": "medium",
            })

        return violations

    async def _consult_analyst_if_needed(
        self,
        agent_id: str,
        files: list[str],
        violations: list[dict[str, Any]],
        state: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Consult Analyst if architectural questions arise.

        Args:
            agent_id: Current agent ID
            files: Files being checked
            violations: Detected violations
            state: Current graph state

        Returns:
            Analyst feedback or None
        """
        # Consult Analyst if:
        # 1. There are high-severity violations
        # 2. Many files are being created/modified
        # 3. Specific architectural patterns are detected

        high_severity_violations = [v for v in violations if v.get("severity") == "high"]

        if high_severity_violations or len(files) > 5:
            question = (
                f"Architecture check: {len(files)} files changed, "
                f"{len(violations)} violations detected. "
                "Please verify architectural consistency."
            )

            from mindflow_backend.nodes.implementations.coding.utils import (
                consult_analyst_architecture,
            )

            consultation = await consult_analyst_architecture(
                agent_id, question, state, timeout=30.0
            )

            return consultation

        return None

    async def _generate_arch_notes(
        self, violations: list[dict[str, Any]], analyst_feedback: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Generate architectural notes.

        Args:
            violations: Detected violations
            analyst_feedback: Feedback from Analyst

        Returns:
            List of architectural notes
        """
        notes = []

        for violation in violations:
            notes.append({
                "type": "violation",
                "file": violation.get("file"),
                "violation_type": violation.get("type"),
                "message": violation.get("message"),
                "severity": violation.get("severity"),
            })

        if analyst_feedback and analyst_feedback.get("success"):
            notes.append({
                "type": "analyst_feedback",
                "feedback": analyst_feedback.get("response"),
            })

        return notes

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "agent_id" not in state:
            errors.append("Missing required input: agent_id")

        if "files_modified" not in state and "files_created" not in state:
            errors.append("Missing required input: files_modified or files_created")

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        return errors
