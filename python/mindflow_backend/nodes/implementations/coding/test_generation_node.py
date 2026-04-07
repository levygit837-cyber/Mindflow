"""TestGenerationNode - Generate tests automatically.

This node generates unit and integration tests automatically based on
the implementation, following project patterns.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class TestGenerationNode(BaseNode):
    """Generate tests automatically.

    This node analyzes the implemented code and automatically generates
    unit tests and integration tests following the project's existing
    test patterns and conventions.
    """

    def __init__(self, node_id: str = "test_generation") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.AGENT,
            category=NodeCategory.LLM_INVOKE,
            description="Generate tests automatically based on implementation.",
        )
        self.config.required_inputs = {
            "files_created",
            "files_modified",
            "working_directory",
            "project_context",
        }
        self.config.outputs = {
            "tests_generated",
            "test_files_created",
            "coverage_estimate",
            "current_phase",
        }

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute test generation."""
        start_time = time.time()
        try:
            files_created = state.get("files_created", [])
            files_modified = state.get("files_modified", [])
            working_directory = state.get("working_directory", ".")
            project_context = state.get("project_context", {})

            all_files = list(set(files_created + files_modified))

            _logger.debug(
                "test_generation_start",
                node_id=self.node_id,
                files_count=len(all_files),
                working_dir=working_directory,
                project_type=project_context.get("project_type", "unknown"),
            )

            # Generate tests
            tests_generated = await self._generate_tests(
                all_files, working_directory, project_context
            )

            # Create test files
            test_files_created = await self._create_test_files(
                tests_generated, working_directory
            )

            # Estimate coverage
            coverage_estimate = await self._estimate_coverage(
                all_files, tests_generated
            )

            result = {
                "tests_generated": tests_generated,
                "test_files_created": test_files_created,
                "coverage_estimate": coverage_estimate,
                "current_phase": "tests_generated",
            }

            duration = time.time() - start_time
            _logger.info(
                "test_generation_complete",
                node_id=self.node_id,
                duration=duration,
                tests_count=len(tests_generated),
                test_files_count=len(test_files_created),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "test_generation_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )
            return {
                "current_phase": "error",
                "error": str(e),
                "tests_generated": [],
                "test_files_created": [],
            }

    async def _generate_tests(
        self, files: list[str], working_directory: str, project_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate tests for files.

        Args:
            files: Files to generate tests for
            working_directory: Working directory
            project_context: Project context

        Returns:
            List of generated tests
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            detect_language,
            read_file_safe,
        )

        tests = []

        for file_path in files:
            try:
                content = await read_file_safe(file_path, working_directory)
                if content is None:
                    continue

                language = await detect_language(file_path)

                # Generate test based on language
                if language == "python":
                    test = await self._generate_python_test(file_path, content, working_directory)
                    if test:
                        tests.append(test)
                elif language in ("typescript", "javascript"):
                    test = await self._generate_js_test(file_path, content, working_directory)
                    if test:
                        tests.append(test)

            except Exception as e:
                _logger.warning("test_generation_failed", file=file_path, error=str(e))

        return tests

    async def _generate_python_test(
        self, file_path: str, working_directory: str
    ) -> dict[str, Any] | None:
        """Generate Python test file using LLM.

        Args:
            file_path: Source file path
            working_directory: Working directory

        Returns:
            Dictionary with test file info or None
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            generate_tests_with_llm,
        )

        project_context = {
            "project_type": "python",
        }

        tests = await generate_tests_with_llm(
            source_files=[file_path],
            working_directory=working_directory,
            project_context=project_context,
        )

        if not tests:
            return None

        test_spec = tests[0]
        test_content = test_spec.get("content", "")

        if not test_content:
            return None

        test_file_path = test_spec.get("test_file")
        test_file_path = test_file_path.replace("/", "/tests/") if test_file_path else None

        return {
            "source_file": file_path,
            "test_file": test_file_path,
            "content": test_content,
            "language": "python",
        }

    async def _generate_js_test(
        self, file_path: str, content: str, working_directory: str
    ) -> dict[str, Any] | None:
        """Generate JavaScript/TypeScript test using LLM.

        Args:
            file_path: Source file path
            content: Source file content
            working_directory: Working directory

        Returns:
            Generated test or None
        """
        from mindflow_backend.nodes.implementations.coding.utils import (
            generate_tests_with_llm,
        )

        project_context = {
            "project_type": "typescript" if ".ts" in file_path else "javascript",
        }

        tests = await generate_tests_with_llm(
            source_files=[file_path],
            working_directory=working_directory,
            project_context=project_context,
        )

        if not tests:
            return None

        test_spec = tests[0]
        test_content = test_spec.get("content", "")

        if not test_content:
            return None

        return {
            "source_file": file_path,
            "test_file": test_spec.get("test_file"),
            "content": test_content,
            "language": test_spec.get("language", "javascript"),
        }

    async def _create_test_files(
        self, tests: list[dict[str, Any]], working_directory: str
    ) -> list[str]:
        """Create test files.

        Args:
            tests: Generated tests
            working_directory: Working directory

        Returns:
            List of created test file paths
        """
        from mindflow_backend.nodes.implementations.coding.utils import write_file_safe

        created_files = []

        for test in tests:
            try:
                result = await write_file_safe(
                    test["test_file"],
                    test["content"],
                    working_directory,
                    create_dirs=True,
                )

                if result["success"]:
                    created_files.append(result["file_path"])
                    _logger.debug("test_file_created", file=result["file_path"])

            except Exception as e:
                _logger.warning("test_file_creation_failed", file=test["test_file"], error=str(e))

        return created_files

    async def _estimate_coverage(
        self, source_files: list[str], tests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Estimate test coverage.

        Args:
            source_files: Source files
            tests: Generated tests

        Returns:
            Dictionary with coverage estimate
        """
        # Simple estimation based on test-to-source ratio
        if not source_files:
            return {"coverage": 0, "reason": "no_source_files"}

        test_count = len(tests)
        source_count = len(source_files)

        # Estimate: each test file covers ~1 source file
        estimated_coverage = min((test_count / source_count) * 100, 100)

        return {
            "coverage": estimated_coverage,
            "source_files": source_count,
            "test_files": test_count,
            "estimate_method": "ratio_based",
        }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if "files_created" not in state and "files_modified" not in state:
            errors.append("Missing required input: files_created or files_modified")

        if "working_directory" not in state:
            errors.append("Missing required input: working_directory")

        if "project_context" not in state:
            errors.append("Missing required input: project_context")

        return errors
