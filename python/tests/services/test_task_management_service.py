"""Tests for TaskManagementService."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text

from mindflow_backend.exceptions.tasks import (
    CircularDependencyError,
    InvalidStatusTransitionError,
    TaskNotFoundError,
    TaskVersionConflictError,
)
from mindflow_backend.infra.database.connection import get_db_session, initialize_database, shutdown_database
from mindflow_backend.schemas.tasks import TaskCreate, TaskUpdate
from mindflow_backend.services.orchestration.task_management_service import TaskManagementService


@pytest_asyncio.fixture(scope="session")
async def init_db():
    """Initialize database for tests."""
    await initialize_database()
    yield
    await shutdown_database()


@pytest_asyncio.fixture
async def task_service(init_db):
    """Create a TaskManagementService instance."""
    return TaskManagementService()


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
async def test_create_task(task_service, clean_tasks):
    """Test creating a basic task."""
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        description="Test Description",
        status="pending",
    )

    task = await task_service.create_task(task_data)

    assert task.id == 1
    assert task.subject == "Test Task"
    assert task.description == "Test Description"
    assert task.status == "pending"
    assert task.version == 1
    assert task.blocks == []
    assert task.blocked_by == []


@pytest.mark.asyncio
async def test_create_task_with_sequential_ids(task_service, clean_tasks):
    """Test that tasks get sequential IDs from high water mark."""
    task1_data = TaskCreate(task_list_id="test_list", subject="Task 1")
    task2_data = TaskCreate(task_list_id="test_list", subject="Task 2")
    task3_data = TaskCreate(task_list_id="test_list", subject="Task 3")

    task1 = await task_service.create_task(task1_data)
    task2 = await task_service.create_task(task2_data)
    task3 = await task_service.create_task(task3_data)

    assert task1.id == 1
    assert task2.id == 2
    assert task3.id == 3


@pytest.mark.asyncio
async def test_get_task(task_service, clean_tasks):
    """Test getting a task by ID."""
    task_data = TaskCreate(task_list_id="test_list", subject="Test Task")
    created_task = await task_service.create_task(task_data)

    retrieved_task = await task_service.get_task(created_task.id)

    assert retrieved_task.id == created_task.id
    assert retrieved_task.subject == created_task.subject


@pytest.mark.asyncio
async def test_get_nonexistent_task(task_service, clean_tasks):
    """Test getting a task that doesn't exist."""
    with pytest.raises(TaskNotFoundError) as exc_info:
        await task_service.get_task(999)

    assert "999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_task(task_service, clean_tasks):
    """Test updating a task."""
    task_data = TaskCreate(task_list_id="test_list", subject="Original Subject")
    created_task = await task_service.create_task(task_data)

    update_data = TaskUpdate(
        subject="Updated Subject",
        description="Updated Description",
        status="in_progress",
    )

    updated_task = await task_service.update_task(created_task.id, update_data)

    assert updated_task.subject == "Updated Subject"
    assert updated_task.description == "Updated Description"
    assert updated_task.status == "in_progress"
    assert updated_task.version == 2  # Version incremented


@pytest.mark.asyncio
async def test_optimistic_locking(task_service, clean_tasks):
    """Test optimistic locking with version conflict."""
    task_data = TaskCreate(task_list_id="test_list", subject="Test Task")
    task = await task_service.create_task(task_data)

    # First update succeeds
    update1 = TaskUpdate(subject="Update 1", version=1)
    updated_task = await task_service.update_task(task.id, update1)
    assert updated_task.version == 2

    # Second update with stale version fails
    update2 = TaskUpdate(subject="Update 2", version=1)
    with pytest.raises(TaskVersionConflictError) as exc_info:
        await task_service.update_task(task.id, update2)

    assert exc_info.value.expected_version == 1
    assert exc_info.value.actual_version == 2


@pytest.mark.asyncio
async def test_invalid_status_transition(task_service, clean_tasks):
    """Test that invalid status transitions are rejected."""
    task_data = TaskCreate(task_list_id="test_list", subject="Test Task", status="completed")
    task = await task_service.create_task(task_data)

    # Cannot transition from completed to pending
    update_data = TaskUpdate(status="pending")

    with pytest.raises(InvalidStatusTransitionError):
        await task_service.update_task(task.id, update_data)


@pytest.mark.asyncio
async def test_create_task_with_dependencies(task_service, clean_tasks):
    """Test creating tasks with dependency relationships."""
    task1_data = TaskCreate(task_list_id="test_list", subject="Task 1")
    task2_data = TaskCreate(task_list_id="test_list", subject="Task 2")

    task1 = await task_service.create_task(task1_data)
    task2 = await task_service.create_task(task2_data)

    # Task 3 blocks task 1 and is blocked by task 2
    task3_data = TaskCreate(
        task_list_id="test_list",
        subject="Task 3",
        blocks=[task1.id],
        blocked_by=[task2.id],
    )

    task3 = await task_service.create_task(task3_data)

    assert task1.id in task3.blocks
    assert task2.id in task3.blocked_by


@pytest.mark.asyncio
async def test_circular_dependency_detection(task_service, clean_tasks):
    """Test that circular dependencies are detected and rejected."""
    task1_data = TaskCreate(task_list_id="test_list", subject="Task 1")
    task2_data = TaskCreate(task_list_id="test_list", subject="Task 2")

    task1 = await task_service.create_task(task1_data)
    task2 = await task_service.create_task(task2_data)

    # Task 1 blocks Task 2
    update1 = TaskUpdate(add_blocks=[task2.id])
    await task_service.update_task(task1.id, update1)

    # Task 2 blocks Task 1 (circular!) - should fail
    update2 = TaskUpdate(add_blocks=[task1.id])

    with pytest.raises(CircularDependencyError) as exc_info:
        await task_service.update_task(task2.id, update2)

    assert task1.id in exc_info.value.cycle
    assert task2.id in exc_info.value.cycle


@pytest.mark.asyncio
async def test_delete_task(task_service, clean_tasks):
    """Test deleting a task."""
    task_data = TaskCreate(task_list_id="test_list", subject="Test Task")
    task = await task_service.create_task(task_data)

    result = await task_service.delete_task(task.id)
    assert result is True

    # Task should no longer exist
    with pytest.raises(TaskNotFoundError):
        await task_service.get_task(task.id)


@pytest.mark.asyncio
async def test_delete_task_cascades_dependencies(task_service, clean_tasks):
    """Test that deleting a task cascades to its dependencies."""
    task1_data = TaskCreate(task_list_id="test_list", subject="Task 1")
    task2_data = TaskCreate(task_list_id="test_list", subject="Task 2")

    task1 = await task_service.create_task(task1_data)
    task2 = await task_service.create_task(task2_data)

    # Task 1 blocks Task 2
    update = TaskUpdate(add_blocks=[task2.id])
    await task_service.update_task(task1.id, update)

    # Delete Task 1
    await task_service.delete_task(task1.id)

    # Task 2 should still exist but dependency should be gone
    task2_after = await task_service.get_task(task2.id)
    assert task1.id not in task2_after.blocked_by


@pytest.mark.asyncio
async def test_list_tasks(task_service, clean_tasks):
    """Test listing tasks with pagination."""
    # Create 5 tasks
    for i in range(5):
        task_data = TaskCreate(task_list_id="test_list", subject=f"Task {i+1}")
        await task_service.create_task(task_data)

    # List all tasks
    response = await task_service.list_tasks(task_list_id="test_list")

    assert len(response.tasks) == 5
    assert response.total == 5


@pytest.mark.asyncio
async def test_list_tasks_with_filters(task_service, clean_tasks):
    """Test listing tasks with filters."""
    # Create tasks with different owners and statuses
    task1_data = TaskCreate(task_list_id="test_list", subject="Task 1", owner="agent1", status="pending")
    task2_data = TaskCreate(task_list_id="test_list", subject="Task 2", owner="agent1", status="in_progress")
    task3_data = TaskCreate(task_list_id="test_list", subject="Task 3", owner="agent2", status="pending")

    await task_service.create_task(task1_data)
    await task_service.create_task(task2_data)
    await task_service.create_task(task3_data)

    # Filter by owner
    response = await task_service.list_tasks(task_list_id="test_list", owner="agent1")
    assert len(response.tasks) == 2
    assert response.total == 2

    # Filter by status
    response = await task_service.list_tasks(task_list_id="test_list", status="pending")
    assert len(response.tasks) == 2
    assert response.total == 2

    # Filter by owner and status
    response = await task_service.list_tasks(
        task_list_id="test_list",
        owner="agent1",
        status="in_progress"
    )
    assert len(response.tasks) == 1
    assert response.total == 1


@pytest.mark.asyncio
async def test_list_tasks_pagination(task_service, clean_tasks):
    """Test task list pagination."""
    # Create 10 tasks
    for i in range(10):
        task_data = TaskCreate(task_list_id="test_list", subject=f"Task {i+1}")
        await task_service.create_task(task_data)

    # Get first page
    response_page1 = await task_service.list_tasks(task_list_id="test_list", limit=5, offset=0)
    assert len(response_page1.tasks) == 5
    assert response_page1.total == 10

    # Get second page
    response_page2 = await task_service.list_tasks(task_list_id="test_list", limit=5, offset=5)
    assert len(response_page2.tasks) == 5
    assert response_page2.total == 10

    # Pages should have different tasks
    page1_ids = {t.id for t in response_page1.tasks}
    page2_ids = {t.id for t in response_page2.tasks}
    assert page1_ids.isdisjoint(page2_ids)
