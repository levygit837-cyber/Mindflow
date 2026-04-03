"""Tests for task management tools."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text

from mindflow_backend.agents.tools.orchestration.task_management_tools import (
    TaskCreateTool,
    TaskGetTool,
    TaskListTool,
    TaskUpdateTool,
)
from mindflow_backend.infra.database.connection import get_db_session, initialize_database, shutdown_database


@pytest_asyncio.fixture(scope="session")
async def init_db():
    """Initialize database for tests."""
    await initialize_database()
    yield
    await shutdown_database()


@pytest_asyncio.fixture
async def clean_tasks(init_db):
    """Clean up tasks before and after tests."""
    async with get_db_session() as db:
        await db.execute(text("DELETE FROM task_dependencies"))
        await db.execute(text("DELETE FROM tasks"))
        await db.execute(text("ALTER SEQUENCE tasks_id_seq RESTART WITH 1"))
        await db.commit()

    yield

    async with get_db_session() as db:
        await db.execute(text("DELETE FROM task_dependencies"))
        await db.execute(text("DELETE FROM tasks"))
        await db.execute(text("ALTER SEQUENCE tasks_id_seq RESTART WITH 1"))
        await db.commit()


@pytest.mark.asyncio
async def test_task_create_tool(clean_tasks):
    """Test TaskCreateTool."""
    tool = TaskCreateTool()

    # Verify schema
    schema = tool.get_schema()
    assert schema["name"] == "task_create"
    assert "task_list_id" in schema["parameters"]["properties"]
    assert "subject" in schema["parameters"]["properties"]

    # Create a task
    result = await tool.execute(
        task_list_id="test_list",
        subject="Test Task",
        description="Test Description",
        status="pending",
    )

    assert result["success"] is True
    assert "task" in result
    assert result["task"]["subject"] == "Test Task"
    assert result["task"]["description"] == "Test Description"
    assert result["task"]["status"] == "pending"
    assert result["task"]["id"] == 1  # First task should have ID 1


@pytest.mark.asyncio
async def test_task_create_tool_with_dependencies(clean_tasks):
    """Test TaskCreateTool with dependencies."""
    tool = TaskCreateTool()

    # Create first task
    result1 = await tool.execute(
        task_list_id="test_list",
        subject="Task 1",
    )
    assert result1["success"] is True
    task1_id = result1["task"]["id"]

    # Create second task that blocks first
    result2 = await tool.execute(
        task_list_id="test_list",
        subject="Task 2",
        blocks=[task1_id],
    )
    assert result2["success"] is True
    assert task1_id in result2["task"]["blocks"]


@pytest.mark.asyncio
async def test_task_create_tool_circular_dependency(clean_tasks):
    """Test TaskCreateTool detects circular dependencies."""
    tool = TaskCreateTool()

    # Create task 1
    result1 = await tool.execute(
        task_list_id="test_list",
        subject="Task 1",
    )
    task1_id = result1["task"]["id"]

    # Create task 2 that blocks task 1
    result2 = await tool.execute(
        task_list_id="test_list",
        subject="Task 2",
        blocks=[task1_id],
    )
    task2_id = result2["task"]["id"]

    # Try to create task 3 that would create a cycle
    result3 = await tool.execute(
        task_list_id="test_list",
        subject="Task 3",
        blocks=[task2_id],
        blocked_by=[task1_id],
    )

    assert result3["success"] is False
    assert result3["error_type"] == "circular_dependency"


@pytest.mark.asyncio
async def test_task_get_tool(clean_tasks):
    """Test TaskGetTool."""
    create_tool = TaskCreateTool()
    get_tool = TaskGetTool()

    # Verify schema
    schema = get_tool.get_schema()
    assert schema["name"] == "task_get"
    assert "task_id" in schema["parameters"]["properties"]

    # Create a task
    create_result = await create_tool.execute(
        task_list_id="test_list",
        subject="Test Task",
        description="Test Description",
    )
    task_id = create_result["task"]["id"]

    # Get the task
    get_result = await get_tool.execute(task_id=task_id)

    assert get_result["success"] is True
    assert get_result["task"]["id"] == task_id
    assert get_result["task"]["subject"] == "Test Task"
    assert get_result["task"]["description"] == "Test Description"


@pytest.mark.asyncio
async def test_task_get_tool_not_found(clean_tasks):
    """Test TaskGetTool with non-existent task."""
    tool = TaskGetTool()

    result = await tool.execute(task_id=99999)

    assert result["success"] is False
    assert result["error_type"] == "not_found"


@pytest.mark.asyncio
async def test_task_update_tool(clean_tasks):
    """Test TaskUpdateTool."""
    create_tool = TaskCreateTool()
    update_tool = TaskUpdateTool()

    # Verify schema
    schema = update_tool.get_schema()
    assert schema["name"] == "task_update"
    assert "task_id" in schema["parameters"]["properties"]
    assert "status" in schema["parameters"]["properties"]

    # Create a task
    create_result = await create_tool.execute(
        task_list_id="test_list",
        subject="Test Task",
        status="pending",
    )
    task_id = create_result["task"]["id"]

    # Update the task
    update_result = await update_tool.execute(
        task_id=task_id,
        status="in_progress",
        subject="Updated Task",
    )

    assert update_result["success"] is True
    assert update_result["task"]["id"] == task_id
    assert update_result["task"]["status"] == "in_progress"
    assert update_result["task"]["subject"] == "Updated Task"
    assert update_result["task"]["version"] == 2  # Version incremented


@pytest.mark.asyncio
async def test_task_update_tool_version_conflict(clean_tasks):
    """Test TaskUpdateTool with version conflict."""
    create_tool = TaskCreateTool()
    update_tool = TaskUpdateTool()

    # Create a task
    create_result = await create_tool.execute(
        task_list_id="test_list",
        subject="Test Task",
    )
    task_id = create_result["task"]["id"]

    # Update with correct version
    await update_tool.execute(
        task_id=task_id,
        status="in_progress",
        version=1,
    )

    # Try to update with old version
    result = await update_tool.execute(
        task_id=task_id,
        status="completed",
        version=1,  # Old version
    )

    assert result["success"] is False
    assert result["error_type"] == "version_conflict"


@pytest.mark.asyncio
async def test_task_update_tool_invalid_transition(clean_tasks):
    """Test TaskUpdateTool with invalid status transition."""
    create_tool = TaskCreateTool()
    update_tool = TaskUpdateTool()

    # Create a completed task
    create_result = await create_tool.execute(
        task_list_id="test_list",
        subject="Test Task",
        status="completed",
    )
    task_id = create_result["task"]["id"]

    # Try to transition back to pending (invalid)
    result = await update_tool.execute(
        task_id=task_id,
        status="pending",
    )

    assert result["success"] is False
    assert result["error_type"] == "invalid_transition"


@pytest.mark.asyncio
async def test_task_list_tool(clean_tasks):
    """Test TaskListTool."""
    create_tool = TaskCreateTool()
    list_tool = TaskListTool()

    # Verify schema
    schema = list_tool.get_schema()
    assert schema["name"] == "task_list"
    assert "task_list_id" in schema["parameters"]["properties"]
    assert "status" in schema["parameters"]["properties"]

    # Create multiple tasks
    await create_tool.execute(
        task_list_id="list1",
        subject="Task 1",
        status="pending",
    )
    await create_tool.execute(
        task_list_id="list1",
        subject="Task 2",
        status="in_progress",
    )
    await create_tool.execute(
        task_list_id="list2",
        subject="Task 3",
        status="pending",
    )

    # List all tasks
    result = await list_tool.execute()
    assert result["success"] is True
    assert result["total"] == 3
    assert len(result["tasks"]) == 3


@pytest.mark.asyncio
async def test_task_list_tool_with_filters(clean_tasks):
    """Test TaskListTool with filters."""
    create_tool = TaskCreateTool()
    list_tool = TaskListTool()

    # Create multiple tasks
    await create_tool.execute(
        task_list_id="list1",
        subject="Task 1",
        status="pending",
        owner="agent1",
    )
    await create_tool.execute(
        task_list_id="list1",
        subject="Task 2",
        status="in_progress",
        owner="agent2",
    )
    await create_tool.execute(
        task_list_id="list2",
        subject="Task 3",
        status="pending",
        owner="agent1",
    )

    # Filter by task_list_id
    result1 = await list_tool.execute(task_list_id="list1")
    assert result1["success"] is True
    assert result1["total"] == 2

    # Filter by status
    result2 = await list_tool.execute(status="pending")
    assert result2["success"] is True
    assert result2["total"] == 2

    # Filter by owner
    result3 = await list_tool.execute(owner="agent1")
    assert result3["success"] is True
    assert result3["total"] == 2

    # Multiple filters
    result4 = await list_tool.execute(task_list_id="list1", status="pending")
    assert result4["success"] is True
    assert result4["total"] == 1


@pytest.mark.asyncio
async def test_task_list_tool_pagination(clean_tasks):
    """Test TaskListTool pagination."""
    create_tool = TaskCreateTool()
    list_tool = TaskListTool()

    # Create 5 tasks
    for i in range(5):
        await create_tool.execute(
            task_list_id="test_list",
            subject=f"Task {i+1}",
        )

    # Get first page
    result1 = await list_tool.execute(skip=0, limit=2)
    assert result1["success"] is True
    assert len(result1["tasks"]) == 2
    assert result1["total"] == 5

    # Get second page
    result2 = await list_tool.execute(skip=2, limit=2)
    assert result2["success"] is True
    assert len(result2["tasks"]) == 2
    assert result2["total"] == 5

    # Get third page
    result3 = await list_tool.execute(skip=4, limit=2)
    assert result3["success"] is True
    assert len(result3["tasks"]) == 1
    assert result3["total"] == 5
