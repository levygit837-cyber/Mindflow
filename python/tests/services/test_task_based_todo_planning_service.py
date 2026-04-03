"""Tests for TaskBasedTodoPlanningService."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text

from mindflow_backend.infra.database.connection import get_db_session, initialize_database, shutdown_database
from mindflow_backend.schemas.tools.planning import TodoItemContract, TodoItemStatus
from mindflow_backend.services.orchestration.task_based_todo_planning_service import (
    TaskBasedTodoPlanningService,
)


@pytest_asyncio.fixture(scope="session")
async def init_db():
    """Initialize database for tests."""
    await initialize_database()
    yield
    await shutdown_database()


@pytest_asyncio.fixture
async def todo_service(init_db):
    """Create a TaskBasedTodoPlanningService instance."""
    # Don't pass task_service - let it lazy initialize via factory function
    return TaskBasedTodoPlanningService()


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
async def test_replace_list_creates_tasks(todo_service, clean_tasks):
    """Test that replace_list creates tasks in database."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="First task",
            owner_agent="analyst",
            priority="high",
            dependencies=[],
            complexity_score=0.5,
        ),
        TodoItemContract(
            item_id="task-2",
            title="Task 2",
            description="Second task",
            owner_agent="coder",
            priority="medium",
            dependencies=["task-1"],
            complexity_score=0.7,
        ),
    ]

    response = await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    assert response.todo_list.session_id == "test_session"
    assert response.todo_list.task_id == "test_task"
    assert response.todo_list.goal == "Test goal"
    assert response.todo_list.source == "test"
    assert len(response.todo_list.items) == 2

    # Verify dependencies
    task2 = next(item for item in response.todo_list.items if item.item_id == "task-2")
    assert "task-1" in task2.dependencies


@pytest.mark.asyncio
async def test_get_list_retrieves_tasks(todo_service, clean_tasks):
    """Test that get_list retrieves tasks from database."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="First task",
            owner_agent="analyst",
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    response = await todo_service.get_list("test_session", "test_task")

    assert response.todo_list.session_id == "test_session"
    assert response.todo_list.task_id == "test_task"
    assert len(response.todo_list.items) == 1
    assert response.todo_list.items[0].title == "Task 1"


@pytest.mark.asyncio
async def test_update_item_status(todo_service, clean_tasks):
    """Test updating item status."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="First task",
            owner_agent="analyst",
            status=TodoItemStatus.PENDING,
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    response = await todo_service.update_item_status(
        session_id="test_session",
        task_id="test_task",
        item_id="task-1",
        status=TodoItemStatus.COMPLETED.value,
        notes="Task completed successfully",
    )

    updated_item = response.todo_list.items[0]
    assert updated_item.status == TodoItemStatus.COMPLETED
    assert updated_item.notes == "Task completed successfully"
    assert updated_item.completed_at is not None


@pytest.mark.asyncio
async def test_focus_complex_items(todo_service, clean_tasks):
    """Test focusing on most complex items."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Simple Task",
            description="Low complexity",
            owner_agent="analyst",
            complexity_score=0.3,
            status=TodoItemStatus.PENDING,
        ),
        TodoItemContract(
            item_id="task-2",
            title="Complex Task",
            description="High complexity",
            owner_agent="arch_tech",
            complexity_score=0.9,
            status=TodoItemStatus.PENDING,
        ),
        TodoItemContract(
            item_id="task-3",
            title="Medium Task",
            description="Medium complexity",
            owner_agent="coder",
            complexity_score=0.6,
            status=TodoItemStatus.PENDING,
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    response = await todo_service.focus_complex_items(
        session_id="test_session",
        task_id="test_task",
        limit=2,
    )

    assert len(response.items) == 2
    # Should be sorted by complexity (highest first)
    assert response.items[0].item_id == "task-2"  # 0.9
    assert response.items[1].item_id == "task-3"  # 0.6


@pytest.mark.asyncio
async def test_replace_list_deletes_old_tasks(todo_service, clean_tasks):
    """Test that replace_list deletes old tasks before creating new ones."""
    # Create initial list
    items1 = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="First task",
            owner_agent="analyst",
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Initial goal",
        items=items1,
        source="test",
    )

    # Replace with new list
    items2 = [
        TodoItemContract(
            item_id="task-2",
            title="Task 2",
            description="Second task",
            owner_agent="coder",
        ),
    ]

    response = await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="New goal",
        items=items2,
        source="test",
    )

    # Should only have new task
    assert len(response.todo_list.items) == 1
    assert response.todo_list.items[0].item_id == "task-2"


@pytest.mark.asyncio
async def test_is_stale(todo_service, clean_tasks):
    """Test stale detection."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="First task",
            owner_agent="analyst",
            status=TodoItemStatus.PENDING,
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    # Should not be stale immediately
    is_stale = await todo_service.is_stale("test_session", "test_task")
    assert is_stale is False


@pytest.mark.asyncio
async def test_close_list(todo_service, clean_tasks):
    """Test closing a todo list."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="First task",
            owner_agent="analyst",
            status=TodoItemStatus.PENDING,
        ),
        TodoItemContract(
            item_id="task-2",
            title="Task 2",
            description="Second task",
            owner_agent="coder",
            status=TodoItemStatus.IN_PROGRESS,
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    response = await todo_service.close_list("test_session", "test_task")

    # All items should be completed
    assert all(item.status == TodoItemStatus.COMPLETED for item in response.todo_list.items)
    assert response.todo_list.closed_at is not None


@pytest.mark.asyncio
async def test_retry_items_failed_only(todo_service, clean_tasks):
    """Test retrying only failed items."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="Completed task",
            owner_agent="analyst",
            status=TodoItemStatus.COMPLETED,
        ),
        TodoItemContract(
            item_id="task-2",
            title="Task 2",
            description="Failed task",
            owner_agent="coder",
            status=TodoItemStatus.FAILED,
        ),
        TodoItemContract(
            item_id="task-3",
            title="Task 3",
            description="Blocked task",
            owner_agent="analyst",
            status=TodoItemStatus.BLOCKED,
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    response = await todo_service.retry_items(
        session_id="test_session",
        task_id="test_task",
        retry_subtasks=False,
        retry_from_beginning=False,
    )

    # task-1 should still be completed
    task1 = next(item for item in response.todo_list.items if item.item_id == "task-1")
    assert task1.status == TodoItemStatus.COMPLETED

    # task-2 and task-3 should be reset to pending
    task2 = next(item for item in response.todo_list.items if item.item_id == "task-2")
    assert task2.status == TodoItemStatus.PENDING

    task3 = next(item for item in response.todo_list.items if item.item_id == "task-3")
    assert task3.status == TodoItemStatus.PENDING


@pytest.mark.asyncio
async def test_retry_items_from_beginning(todo_service, clean_tasks):
    """Test retrying all items from beginning."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="Completed task",
            owner_agent="analyst",
            status=TodoItemStatus.COMPLETED,
        ),
        TodoItemContract(
            item_id="task-2",
            title="Task 2",
            description="Failed task",
            owner_agent="coder",
            status=TodoItemStatus.FAILED,
        ),
    ]

    await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    response = await todo_service.retry_items(
        session_id="test_session",
        task_id="test_task",
        retry_subtasks=False,
        retry_from_beginning=True,
    )

    # All items should be reset to pending
    assert all(item.status == TodoItemStatus.PENDING for item in response.todo_list.items)


@pytest.mark.asyncio
async def test_summary_statistics(todo_service, clean_tasks):
    """Test summary statistics calculation."""
    items = [
        TodoItemContract(
            item_id="task-1",
            title="Task 1",
            description="Completed",
            owner_agent="analyst",
            status=TodoItemStatus.COMPLETED,
            complexity_score=0.5,
        ),
        TodoItemContract(
            item_id="task-2",
            title="Task 2",
            description="Pending",
            owner_agent="coder",
            status=TodoItemStatus.PENDING,
            complexity_score=0.3,
        ),
        TodoItemContract(
            item_id="task-3",
            title="Task 3",
            description="Failed",
            owner_agent="analyst",
            status=TodoItemStatus.FAILED,
            complexity_score=0.7,
        ),
    ]

    response = await todo_service.replace_list(
        session_id="test_session",
        task_id="test_task",
        goal="Test goal",
        items=items,
        source="test",
    )

    summary = response.summary
    assert summary.total_items == 3
    assert summary.completed_items == 1
    assert summary.open_items == 2  # pending + failed
    assert summary.failed_items == 1
    assert summary.progress_percentage > 0
    assert summary.highest_open_complexity == 0.7
