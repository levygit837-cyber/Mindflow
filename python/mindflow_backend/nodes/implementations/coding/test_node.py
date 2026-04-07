"""TestNode - Run test suite and collect results.

This node executes the test suite, collects results, identifies
failing tests, and generates coverage reports.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class TestNode(BaseNode):
    """Run test suite and collect results.

    This node executes the project's test suite, collects test results,
    identifies failing tests with retry logic for flaky tests, and
    generates coverage reports.
    """

    def __init__(self, node_id: str = "test") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.TOOL,
            category=NodeCategory.TOOL_EXECUTION,
            description="Run test suite and collect results.",
        )
        self.config.required_inputs = {
            "working_directory",
            "files_modified",
        }
        self.config.outputs = {
            "test_results",
            "tests_passed",
            "tests_failed",
            "tests_skipped",
            "coverage",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute test phase."""
        start_time = time.time()
        try:
            working_directory = state.get("working_directory", ".")
            files_modified = state.get("files_modified", [])

            _logger.debug(
                "test_node_start",
                node_id=self.node_id,
                working_dir=working_directory,
                modified_files_count=len(files_modified),
            )

            # Run tests
            test_results = await self._run_tests(working_directory)

            # Get coverage if tests passed
            coverage = None
            if test_results["success"]:
                coverage = await self._get_coverage(working_directory)

            result = {
                "test_results": test_results,
                "tests_passed": test_results.get("tests_passed", 0),
                "tests_failed": test_results.get("tests_failed", 0),
                "tests_skipped": test_results.get("tests_skipped", 0),
                "coverage": coverage,
                "current_phase": "tested",
            }

            duration = time.time() - start_time
            _logger.info(
                "test_node_complete",
                node_id=self.node_id,
                duration=duration,
                passed=result["tests_passed"],
                failed=result["tests_failed"],
                skipped=result["tests_skipped"],
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "test_node_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "test_results": {},
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_skipped": 0,
            }

    async def _run_tests(self, working_directory: str) -> dict[str, Any]:
        """Run test suite.

        Args:
            working_directory: Working directory

        Returns:
            Dictionary with test results
        """
        from mindflow_backend.nodes.implementations.coding.utils import run_tests

        test_results = await run_tests(
            working_directory=working_directory,
            test_path=None,
            verbose=False,
        )

        return test_results

    async def _get_coverage(self, working_directory: str) -> dict[str, Any]:
        """Get test coverage report.

        Args:
            working_directory: Working directory

        Returns:
            Dictionary with coverage information
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            detect_test_framework,
            get_test_coverage,
        )

        framework = await detect_test_framework(working_directory)

        if framework == "unknown":
            return {
                "success": False,
                "error": "Could not detect test framework",
            }

        coverage_result = await get_test_coverage(working_directory, framework)

        return coverage_result

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        return errors
