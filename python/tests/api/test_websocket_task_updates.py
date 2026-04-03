"""Tests for WebSocket task updates functionality."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fastapi import WebSocket
from sqlalchemy import text

from mindflow_backend.api.websocket.task_updates import (
    TaskUpdateMessage,
    TaskUpdateSubscription,
    TaskUpdateWebSocketManager,
    WebSocketConnection,
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


@pytest_asyncio.fixture
async def ws_manager():
    """Create a fresh WebSocket manager for each test."""
    # Reset singleton
    TaskUpdateWebSocketManager._instance = None
    manager = await TaskUpdateWebSocketManager.get_instance()
    yield manager
    # Cleanup
    manager._connections.clear()
    if manager._broadcast_task and not manager._broadcast_task.done():
        manager._broadcast_task.cancel()
        try:
            await manager._broadcast_task
        except asyncio.CancelledError:
            pass


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages: list[dict] = []
        self.accepted = False
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data: dict):
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages.append(data)

    async def receive_json(self):
        # Simulate waiting forever (connection stays open)
        await asyncio.sleep(3600)

    def get_messages(self) -> list[dict]:
        return self.messages


@pytest.mark.asyncio
async def test_websocket_connection_matches_filter():
    """Test that WebSocketConnection correctly filters messages."""
    mock_ws = MockWebSocket()
    subscription = TaskUpdateSubscription(task_list_id="test_list")
    connection = WebSocketConnection(mock_ws, "conn_1", subscription)

    # Message matching filter
    matching_message = TaskUpdateMessage(
        event_type="task_created",
        task_id=1,
        task_list_id="test_list",
        subject="Test Task",
        status="pending",
        timestamp=datetime.now(UTC).isoformat(),
    )
    assert connection.matches_filter(matching_message) is True

    # Message not matching filter
    non_matching_message = TaskUpdateMessage(
        event_type="task_created",
        task_id=2,
        task_list_id="other_list",
        subject="Other Task",
        status="pending",
        timestamp=datetime.now(UTC).isoformat(),
    )
    assert connection.matches_filter(non_matching_message) is False


@pytest.mark.asyncio
async def test_websocket_connection_no_filter_receives_all():
    """Test that connection with no filters receives all messages."""
    mock_ws = MockWebSocket()
    subscription = TaskUpdateSubscription()  # No filters
    connection = WebSocketConnection(mock_ws, "conn_1", subscription)

    message1 = TaskUpdateMessage(
        event_type="task_created",
        task_id=1,
        task_list_id="list_1",
        subject="Task 1",
        status="pending",
        timestamp=datetime.now(UTC).isoformat(),
    )
    message2 = TaskUpdateMessage(
        event_type="task_created",
        task_id=2,
        task_list_id="list_2",
        subject="Task 2",
        status="pending",
        timestamp=datetime.now(UTC).isoformat(),
    )

    assert connection.matches_filter(message1) is True
    assert connection.matches_filter(message2) is True


@pytest.mark.asyncio
async def test_websocket_manager_connect_disconnect(ws_manager):
    """Test WebSocket manager connection and disconnection."""
    mock_ws = MockWebSocket()
    subscription = TaskUpdateSubscription(task_list_id="test_list")

    # Connect
    connection_id = await ws_manager.connect(mock_ws, subscription)
    assert mock_ws.accepted is True
    assert ws_manager.get_connection_count() == 1

    # Disconnect
    await ws_manager.disconnect(connection_id)
    assert ws_manager.get_connection_count() == 0


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_to_matching_connections(ws_manager):
    """Test that manager broadcasts only to matching connections."""
    # Create two connections with different filters
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()

    subscription1 = TaskUpdateSubscription(task_list_id="list_1")
    subscription2 = TaskUpdateSubscription(task_list_id="list_2")

    await ws_manager.connect(mock_ws1, subscription1)
    await ws_manager.connect(mock_ws2, subscription2)

    # Broadcast message for list_1
    message = TaskUpdateMessage(
        event_type="task_created",
        task_id=1,
        task_list_id="list_1",
        subject="Test Task",
        status="pending",
        timestamp=datetime.now(UTC).isoformat(),
    )

    await ws_manager.broadcast_task_update(message)

    # Wait for broadcast worker to process
    await asyncio.sleep(0.1)

    # Only ws1 should receive the message
    assert len(mock_ws1.get_messages()) == 1
    assert len(mock_ws2.get_messages()) == 0
    assert mock_ws1.get_messages()[0]["task_id"] == 1


@pytest.mark.asyncio
async def test_task_created_broadcasts_websocket_update(task_service, clean_tasks, ws_manager):
    """Test that creating a task broadcasts WebSocket update."""
    # Connect a WebSocket client
    mock_ws = MockWebSocket()
    subscription = TaskUpdateSubscription(task_list_id="test_list")
    await ws_manager.connect(mock_ws, subscription)

    # Create a task
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        description="Test Description",
    )

    task = await task_service.create_task(task_data, session_id="test_session")

    # Wait for broadcast
    await asyncio.sleep(0.1)

    # Verify WebSocket received the message
    messages = mock_ws.get_messages()
    assert len(messages) == 1
    assert messages[0]["event_type"] == "task_created"
    assert messages[0]["task_id"] == task.id
    assert messages[0]["subject"] == "Test Task"
    assert messages[0]["task_list_id"] == "test_list"


@pytest.mark.asyncio
async def test_task_completed_broadcasts_websocket_update(task_service, clean_tasks, ws_manager):
    """Test that completing a task broadcasts WebSocket update."""
    # Connect a WebSocket client
    mock_ws = MockWebSocket()
    subscription = TaskUpdateSubscription(task_list_id="test_list")
    await ws_manager.connect(mock_ws, subscription)

    # Create a task with in_progress status
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        status="in_progress",
    )
    task = await task_service.create_task(task_data, session_id="test_session")

    # Clear messages from creation
    mock_ws.messages.clear()

    # Update task to completed
    update_data = TaskUpdate(status="completed")
    await task_service.update_task(task.id, update_data, session_id="test_session")

    # Wait for broadcast
    await asyncio.sleep(0.1)

    # Verify WebSocket received the completed message
    messages = mock_ws.get_messages()
    assert len(messages) == 1
    assert messages[0]["event_type"] == "task_completed"
    assert messages[0]["task_id"] == task.id
    assert messages[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_task_updated_broadcasts_websocket_update(task_service, clean_tasks, ws_manager):
    """Test that updating a task (non-completed) broadcasts WebSocket update."""
    # Connect a WebSocket client
    mock_ws = MockWebSocket()
    subscription = TaskUpdateSubscription(task_list_id="test_list")
    await ws_manager.connect(mock_ws, subscription)

    # Create a task
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
        status="pending",
    )
    task = await task_service.create_task(task_data, session_id="test_session")

    # Clear messages from creation
    mock_ws.messages.clear()

    # Update task subject
    update_data = TaskUpdate(subject="Updated Subject")
    await task_service.update_task(task.id, update_data, session_id="test_session")

    # Wait for broadcast
    await asyncio.sleep(0.1)

    # Verify WebSocket received the update message
    messages = mock_ws.get_messages()
    assert len(messages) == 1
    assert messages[0]["event_type"] == "task_updated"
    assert messages[0]["task_id"] == task.id
    assert messages[0]["subject"] == "Updated Subject"


@pytest.mark.asyncio
async def test_websocket_filter_by_session_id(task_service, clean_tasks, ws_manager):
    """Test WebSocket filtering by session_id."""
    # Connect two clients with different session filters
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()

    subscription1 = TaskUpdateSubscription(session_id="session_1")
    subscription2 = TaskUpdateSubscription(session_id="session_2")

    await ws_manager.connect(mock_ws1, subscription1)
    await ws_manager.connect(mock_ws2, subscription2)

    # Create task with session_1
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
    )
    await task_service.create_task(task_data, session_id="session_1")

    # Wait for broadcast
    await asyncio.sleep(0.1)

    # Only ws1 should receive the message
    assert len(mock_ws1.get_messages()) == 1
    assert len(mock_ws2.get_messages()) == 0


@pytest.mark.asyncio
async def test_websocket_no_broadcast_without_session_id(task_service, clean_tasks, ws_manager):
    """Test that no WebSocket broadcast happens when session_id is None."""
    # Connect a WebSocket client
    mock_ws = MockWebSocket()
    subscription = TaskUpdateSubscription()
    await ws_manager.connect(mock_ws, subscription)

    # Create task without session_id
    task_data = TaskCreate(
        task_list_id="test_list",
        subject="Test Task",
    )
    await task_service.create_task(task_data, session_id=None)

    # Wait for potential broadcast
    await asyncio.sleep(0.1)

    # No messages should be received
    assert len(mock_ws.get_messages()) == 0
