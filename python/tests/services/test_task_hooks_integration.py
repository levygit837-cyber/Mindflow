"""Tests for TaskManagementService hook integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import text

from mindflow_backend.hooks.result import HookResult
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
async def test_task_created_hook_triggered(task_service, clean_tasks):
    """Test that TaskCreated hook is triggered when creating a task with session_id."""
    mock_hook_result = HookResult(
        event="task_created",
        command="test_command",
        status="success",
        raw_output="Hook executed successfully",
    )

    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCreatedHandler.execute"
    ) as mock_execute:
        # Setup mock to yield a result
        async def mock_generator(*args, **kwargs):
            yield mock_hook_result

        mock_execute.return_value = mock_generator()

        # Create task with session_id
        task_data = TaskCreate(
            task_list_id="test_list",
            subject="Test Task",
            description="Test Description",
        )

        task = await task_service.create_task(task_data, session_id="test_session_123")

        # Verify hook was called
        mock_execute.assert_called_once()
        call_kwargs = mock_execute.call_args.kwargs
        assert call_kwargs["session_id"] == "test_session_123"
        assert call_kwargs["task_id"] == str(task.id)
        assert call_kwargs["task_name"] == "Test Task"


@pytest.mark.asyncio
async def test_task_created_hook_not_triggered_without_session(task_service, clean_tasks):
    """Test that TaskCreated hook is NOT triggered when session_id is None."""
    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCreatedHandler.execute"
    ) as mock_execute:
        # Create task without session_id
        task_data = TaskCreate(
            task_list_id="test_list",
            subject="Test Task",
        )

        await task_service.create_task(task_data, session_id=None)

        # Verify hook was NOT called
        mock_execute.assert_not_called()


@pytest.mark.asyncio
async def test_task_created_hook_failure_does_not_break_creation(task_service, clean_tasks):
    """Test that task creation succeeds even if hook fails."""
    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCreatedHandler.execute"
    ) as mock_execute:
        # Setup mock to raise exception
        async def mock_generator(*args, **kwargs):
            raise RuntimeError("Hook execution failed")
            yield  # Never reached

        mock_execute.return_value = mock_generator()

        # Create task with session_id
        task_data = TaskCreate(
            task_list_id="test_list",
            subject="Test Task",
        )

        # Should succeed despite hook failure
        task = await task_service.create_task(task_data, session_id="test_session_123")

        assert task.id == 1
        assert task.subject == "Test Task"


@pytest.mark.asyncio
async def test_task_completed_hook_triggered(task_service, clean_tasks):
    """Test that TaskCompleted hook is triggered when status changes to completed."""
    mock_hook_result = HookResult(
        event="task_completed",
        command="test_command",
        status="success",
        raw_output="Hook executed successfully",
    )

    # Create initial task
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        status="in_progress",  # Start with in_progress so we can transition to completed
    )
    task = await task_service.create_task(task_data)

    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCompletedHandler.execute"
    ) as mock_execute:
        # Setup mock to yield a result
        async def mock_generator(*args, **kwargs):
            yield mock_hook_result

        mock_execute.return_value = mock_generator()

        # Update task to completed status
        update_data = TaskUpdate(status="completed")
        updated_task = await task_service.update_task(
            task.id, update_data, session_id="test_session_123"
        )

        # Verify hook was called
        mock_execute.assert_called_once()
        call_kwargs = mock_execute.call_args.kwargs
        assert call_kwargs["session_id"] == "test_session_123"
        assert call_kwargs["task_id"] == str(task.id)
        assert call_kwargs["task_name"] == "Test Task"
        assert updated_task.status == "completed"


@pytest.mark.asyncio
async def test_task_completed_hook_not_triggered_for_other_status(task_service, clean_tasks):
    """Test that TaskCompleted hook is NOT triggered for non-completed status changes."""
    # Create initial task
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        status="pending",
    )
    task = await task_service.create_task(task_data)

    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCompletedHandler.execute"
    ) as mock_execute:
        # Update task to in_progress (not completed)
        update_data = TaskUpdate(status="in_progress")
        await task_service.update_task(task.id, update_data, session_id="test_session_123")

        # Verify hook was NOT called
        mock_execute.assert_not_called()


@pytest.mark.asyncio
async def test_task_completed_hook_not_triggered_without_session(task_service, clean_tasks):
    """Test that TaskCompleted hook is NOT triggered when session_id is None."""
    # Create initial task
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        status="in_progress",  # Start with in_progress so we can transition to completed
    )
    task = await task_service.create_task(task_data)

    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCompletedHandler.execute"
    ) as mock_execute:
        # Update task to completed without session_id
        update_data = TaskUpdate(status="completed")
        await task_service.update_task(task.id, update_data, session_id=None)

        # Verify hook was NOT called
        mock_execute.assert_not_called()


@pytest.mark.asyncio
async def test_task_completed_hook_not_triggered_without_status_change(task_service, clean_tasks):
    """Test that TaskCompleted hook is NOT triggered when status is not updated."""
    # Create initial task
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        status="pending",
    )
    task = await task_service.create_task(task_data)

    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCompletedHandler.execute"
    ) as mock_execute:
        # Update task subject only (no status change)
        update_data = TaskUpdate(subject="Updated Subject")
        await task_service.update_task(task.id, update_data, session_id="test_session_123")

        # Verify hook was NOT called
        mock_execute.assert_not_called()


@pytest.mark.asyncio
async def test_task_completed_hook_failure_does_not_break_update(task_service, clean_tasks):
    """Test that task update succeeds even if hook fails."""
    # Create initial task
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        status="in_progress",  # Start with in_progress so we can transition to completed
    )
    task = await task_service.create_task(task_data)

    with patch(
        "mindflow_backend.services.orchestration.task_management_service.TaskCompletedHandler.execute"
    ) as mock_execute:
        # Setup mock to raise exception
        async def mock_generator(*args, **kwargs):
            raise RuntimeError("Hook execution failed")
            yield  # Never reached

        mock_execute.return_value = mock_generator()

        # Update task to completed
        update_data = TaskUpdate(status="completed")
        updated_task = await task_service.update_task(
            task.id, update_data, session_id="test_session_123"
        )

        # Should succeed despite hook failure
        assert updated_task.status == "completed"
        assert updated_task.version == 2
