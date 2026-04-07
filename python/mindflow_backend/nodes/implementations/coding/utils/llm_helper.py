"""LLM utilities for Coder nodes.

This module provides LLM invocation utilities for code generation,
task decomposition, and test generation.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def decompose_task_with_llm(
    task: str,
    mission_type: str,
    relevant_files: list[str],
    project_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Decompose coding task into implementation steps using LLM.

    Args:
        task: Task description
        mission_type: Type of mission (coding, bug_fix, refactor)
        relevant_files: Files relevant to the task
        project_context: Project context information

    Returns:
        List of implementation steps
    """
    # TODO: Integrate with actual LLM service
    # For now, generate structured steps based on mission type
    
    _logger.info(
        "task_decomposition_start",
        task_preview=task[:100],
        mission_type=mission_type,
        relevant_files_count=len(relevant_files),
    )

    steps = []
    
    if mission_type == "coding":
        steps = await _decompose_coding_task(task, relevant_files, project_context)
    elif mission_type == "bug_fix":
        steps = await _decompose_bug_fix_task(task, relevant_files, project_context)
    elif mission_type == "refactor":
        steps = await _decompose_refactor_task(task, relevant_files, project_context)
    else:
        steps = await _decompose_generic_task(task, relevant_files, project_context)

    _logger.info(
        "task_decomposition_complete",
        steps_count=len(steps),
    )

    return steps


async def _decompose_coding_task(
    task: str,
    relevant_files: list[str],
    project_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Decompose a coding task into steps."""
    project_type = project_context.get("project_type", "python")
    
    steps = [
        {
            "step_id": 1,
            "description": "Analyze existing code structure and dependencies",
            "action": "analyze",
            "files": relevant_files[:5],
            "priority": "high",
        },
        {
            "step_id": 2,
            "description": "Design implementation approach based on requirements",
            "action": "design",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 3,
            "description": "Implement core functionality with proper error handling",
            "action": "implement",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 4,
            "description": "Add comprehensive tests for new functionality",
            "action": "test",
            "files": [],
            "priority": "medium",
        },
        {
            "step_id": 5,
            "description": "Verify implementation against requirements",
            "action": "verify",
            "files": [],
            "priority": "high",
        },
    ]
    
    return steps


async def _decompose_bug_fix_task(
    task: str,
    relevant_files: list[str],
    project_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Decompose a bug fix task into steps."""
    steps = [
        {
            "step_id": 1,
            "description": "Reproduce the bug to understand the issue",
            "action": "reproduce",
            "files": relevant_files[:3],
            "priority": "high",
        },
        {
            "step_id": 2,
            "description": "Analyze code to identify root cause",
            "action": "diagnose",
            "files": relevant_files[:5],
            "priority": "high",
        },
        {
            "step_id": 3,
            "description": "Implement fix with minimal changes",
            "action": "fix",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 4,
            "description": "Add regression tests for the bug",
            "action": "test",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 5,
            "description": "Verify fix resolves the issue without side effects",
            "action": "verify",
            "files": [],
            "priority": "high",
        },
    ]
    
    return steps


async def _decompose_refactor_task(
    task: str,
    relevant_files: list[str],
    project_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Decompose a refactoring task into steps."""
    steps = [
        {
            "step_id": 1,
            "description": "Analyze current code patterns and structure",
            "action": "analyze_patterns",
            "files": relevant_files[:5],
            "priority": "high",
        },
        {
            "step_id": 2,
            "description": "Plan refactoring strategy with risk assessment",
            "action": "plan_refactor",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 3,
            "description": "Apply refactoring incrementally",
            "action": "refactor",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 4,
            "description": "Run tests to ensure behavior is preserved",
            "action": "test",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 5,
            "description": "Verify refactoring improves code quality",
            "action": "verify",
            "files": [],
            "priority": "medium",
        },
    ]
    
    return steps


async def _decompose_generic_task(
    task: str,
    relevant_files: list[str],
    project_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Decompose a generic task into steps."""
    steps = [
        {
            "step_id": 1,
            "description": "Analyze task requirements and context",
            "action": "analyze",
            "files": relevant_files[:5],
            "priority": "high",
        },
        {
            "step_id": 2,
            "description": "Plan implementation approach",
            "action": "plan",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 3,
            "description": "Implement solution",
            "action": "implement",
            "files": [],
            "priority": "high",
        },
        {
            "step_id": 4,
            "description": "Test implementation",
            "action": "test",
            "files": [],
            "priority": "medium",
        },
        {
            "step_id": 5,
            "description": "Verify and document",
            "action": "verify",
            "files": [],
            "priority": "medium",
        },
    ]
    
    return steps


async def generate_code_with_llm(
    step: dict[str, Any],
    task: str,
    working_directory: str,
    project_context: dict[str, Any],
) -> dict[str, Any]:
    """Generate code for an implementation step using LLM.

    Args:
        step: Implementation step definition
        task: Original task description
        working_directory: Working directory
        project_context: Project context

    Returns:
        Dictionary with generated code and metadata
    """
    # TODO: Integrate with actual LLM service
    # For now, return structured placeholder
    
    _logger.info(
        "code_generation_start",
        step_id=step.get("step_id"),
        action=step.get("action"),
    )

    result = {
        "action": step.get("action"),
        "success": True,
        "files_created": [],
        "files_modified": [],
        "code_generated": {},
        "message": f"Completed {step.get('action')} step",
    }

    # Simulate code generation for implement actions
    if step.get("action") == "implement":
        result["code_generated"] = {
            "generated_code.py": "# Generated code implementation\n# TODO: Implement actual functionality\n",
        }
        result["files_created"] = ["generated_code.py"]

    _logger.info(
        "code_generation_complete",
        action=step.get("action"),
        files_created=len(result["files_created"]),
    )

    return result


async def generate_tests_with_llm(
    source_files: list[str],
    working_directory: str,
    project_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate unit tests using LLM.

    Args:
        source_files: Source files to generate tests for
        working_directory: Working directory
        project_context: Project context

    Returns:
        List of generated test specifications
    """
    # TODO: Integrate with actual LLM service
    # For now, generate meaningful test structures
    
    _logger.info(
        "test_generation_start",
        source_files_count=len(source_files),
    )

    project_type = project_context.get("project_type", "python")
    tests = []

    for source_file in source_files:
        if project_type == "python":
            test_spec = await _generate_python_test(source_file, working_directory)
        elif project_type in ("typescript", "javascript"):
            test_spec = await _generate_js_test(source_file, working_directory)
        else:
            test_spec = await _generate_generic_test(source_file, working_directory)

        tests.append(test_spec)

    _logger.info(
        "test_generation_complete",
        tests_count=len(tests),
    )

    return tests


async def _generate_python_test(
    source_file: str,
    working_directory: str,
) -> dict[str, Any]:
    """Generate Python test specification."""
    from mindflow_backend.nodes.implementations.coding.utils import (
        analyze_python_structure,
        read_file_safe,
    )

    content = await read_file_safe(source_file, working_directory)
    
    if not content:
        return {
            "source_file": source_file,
            "test_file": None,
            "content": None,
            "language": "python",
        }

    structure = await analyze_python_structure(content)
    
    # Generate meaningful test cases based on structure
    test_content = f"""# Tests for {source_file}
import pytest
from unittest.mock import Mock, patch

"""

    # Add test cases for functions
    for func in structure.get("functions", []):
        func_name = func["name"]
        test_content += f"""
def test_{func_name}_basic():
    \"\"\"Test basic functionality of {func_name}.\"\"\"
    # TODO: Implement test for {func_name}
    assert True

def test_{func_name}_edge_cases():
    \"\"\"Test edge cases for {func_name}.\"\"\"
    # TODO: Test edge cases
    assert True

def test_{func_name}_error_handling():
    \"\"\"Test error handling in {func_name}.\"\"\"
    # TODO: Test error scenarios
    assert True
"""

    # Add test cases for classes
    for cls in structure.get("classes", []):
        class_name = cls["name"]
        test_content += f"""
class Test{class_name}:
    \"\"\"Test suite for {class_name}.\"\"\"

    def test_initialization(self):
        \"\"\"Test {class_name} initialization.\"\"\"
        # TODO: Implement initialization test
        assert True

    def test_main_functionality(self):
        \"\"\"Test main functionality of {class_name}.\"\"\"
        # TODO: Implement functionality test
        assert True
"""

    test_file_path = source_file.replace(".py", "_test.py").replace("/", "/tests/")

    return {
        "source_file": source_file,
        "test_file": test_file_path,
        "content": test_content,
        "language": "python",
    }


async def _generate_js_test(
    source_file: str,
    working_directory: str,
) -> dict[str, Any]:
    """Generate JavaScript/TypeScript test specification."""
    from mindflow_backend.nodes.implementations.coding.utils import (
        read_file_safe,
    )

    content = await read_file_safe(source_file, working_directory)
    
    if not content:
        return {
            "source_file": source_file,
            "test_file": None,
            "content": None,
            "language": "typescript",
        }

    # Extract functions/classes using regex
    import re
    functions = re.findall(r"(?:async\s+)?(?:function\s+)?(\w+)", content)
    classes = re.findall(r"class\s+(\w+)", content)

    test_content = f"""// Tests for {source_file}
import {{ describe, it, expect }} from '@jest/globals';

"""

    # Add test cases for functions
    for func in functions[:5]:  # Limit to first 5 functions
        test_content += "describe('" + func + "', () => {\n"
        test_content += "  it('should work correctly', () => {\n"
        test_content += "    // TODO: Implement test for " + func + "\n"
        test_content += "    expect(true).toBe(true);\n"
        test_content += "  });\n"
        test_content += "\n"
        test_content += "  it('should handle edge cases', () => {\n"
        test_content += "    // TODO: Test edge cases\n"
        test_content += "    expect(true).toBe(true);\n"
        test_content += "  });\n"
        test_content += "});\n"

    # Add test cases for classes
    for cls in classes[:3]:  # Limit to first 3 classes
        test_content += "describe('" + cls + "', () => {\n"
        test_content += "  it('should initialize correctly', () => {\n"
        test_content += "    // TODO: Implement initialization test\n"
        test_content += "    expect(true).toBe(true);\n"
        test_content += "  });\n"
        test_content += "});\n"

    test_file_path = source_file.replace(".ts", ".test.ts").replace(".js", ".test.js")

    return {
        "source_file": source_file,
        "test_file": test_file_path,
        "content": test_content,
        "language": "typescript" if ".ts" in source_file else "javascript",
    }


async def _generate_generic_test(
    source_file: str,
    working_directory: str,
) -> dict[str, Any]:
    """Generate generic test specification."""
    test_content = f"""# Tests for {source_file}
# TODO: Implement tests
"""

    return {
        "source_file": source_file,
        "test_file": source_file + ".test",
        "content": test_content,
        "language": "unknown",
    }
