"""Test suite for LLM helper utilities."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_decompose_task_with_llm_coding():
    """Test task decomposition for coding mission."""
    from mindflow_backend.nodes.implementations.coding.utils.llm_helper import (
        decompose_task_with_llm,
    )

    task = "Implement a user authentication system"
    mission_type = "coding"
    relevant_files = ["auth.py", "user.py"]
    project_context = {"project_type": "python", "total_files": 10}

    steps = await decompose_task_with_llm(
        task=task,
        mission_type=mission_type,
        relevant_files=relevant_files,
        project_context=project_context,
    )

    assert isinstance(steps, list)
    assert len(steps) > 0
    assert all("step_id" in step for step in steps)
    assert all("description" in step for step in steps)
    assert all("action" in step for step in steps)


@pytest.mark.asyncio
async def test_decompose_task_with_llm_bug_fix():
    """Test task decomposition for bug fix mission."""
    from mindflow_backend.nodes.implementations.coding.utils.llm_helper import (
        decompose_task_with_llm,
    )

    task = "Fix authentication token expiration bug"
    mission_type = "bug_fix"
    relevant_files = ["auth.py"]
    project_context = {"project_type": "python", "total_files": 5}

    steps = await decompose_task_with_llm(
        task=task,
        mission_type=mission_type,
        relevant_files=relevant_files,
        project_context=project_context,
    )

    assert isinstance(steps, list)
    assert len(steps) > 0
    # Bug fix should have reproduce and diagnose steps
    actions = [step["action"] for step in steps]
    assert "reproduce" in actions or "diagnose" in actions


@pytest.mark.asyncio
async def test_decompose_task_with_llm_refactor():
    """Test task decomposition for refactor mission."""
    from mindflow_backend.nodes.implementations.coding.utils.llm_helper import (
        decompose_task_with_llm,
    )

    task = "Refactor authentication module for better separation of concerns"
    mission_type = "refactor"
    relevant_files = ["auth.py", "models.py"]
    project_context = {"project_type": "python", "total_files": 8}

    steps = await decompose_task_with_llm(
        task=task,
        mission_type=mission_type,
        relevant_files=relevant_files,
        project_context=project_context,
    )

    assert isinstance(steps, list)
    assert len(steps) > 0
    # Refactor should have analyze_patterns and refactor steps
    actions = [step["action"] for step in steps]
    assert "analyze_patterns" in actions or "refactor" in actions


@pytest.mark.asyncio
async def test_generate_code_with_llm():
    """Test code generation for implementation step."""
    from mindflow_backend.nodes.implementations.coding.utils.llm_helper import (
        generate_code_with_llm,
    )

    step = {
        "step_id": 1,
        "description": "Implement core functionality",
        "action": "implement",
        "files": [],
    }
    task = "Implement user authentication"
    working_directory = "/tmp/test"
    project_context = {"project_type": "python"}

    result = await generate_code_with_llm(
        step=step,
        task=task,
        working_directory=working_directory,
        project_context=project_context,
    )

    assert isinstance(result, dict)
    assert "action" in result
    assert "success" in result
    assert result["action"] == "implement"


@pytest.mark.asyncio
async def test_generate_tests_with_llm_python():
    """Test test generation for Python files."""
    from mindflow_backend.nodes.implementations.coding.utils.llm_helper import (
        generate_tests_with_llm,
    )

    source_files = ["auth.py"]
    working_directory = "/tmp/test"
    project_context = {"project_type": "python"}

    tests = await generate_tests_with_llm(
        source_files=source_files,
        working_directory=working_directory,
        project_context=project_context,
    )

    assert isinstance(tests, list)
    assert len(tests) > 0
    assert all("source_file" in test for test in tests)
    assert all("test_file" in test for test in tests)
    assert all("content" in test for test in tests)


@pytest.mark.asyncio
async def test_generate_tests_with_llm_javascript():
    """Test test generation for JavaScript files."""
    from mindflow_backend.nodes.implementations.coding.utils.llm_helper import (
        generate_tests_with_llm,
    )

    source_files = ["auth.js"]
    working_directory = "/tmp/test"
    project_context = {"project_type": "javascript"}

    tests = await generate_tests_with_llm(
        source_files=source_files,
        working_directory=working_directory,
        project_context=project_context,
    )

    assert isinstance(tests, list)
    assert len(tests) > 0
    assert all("language" in test for test in tests)
