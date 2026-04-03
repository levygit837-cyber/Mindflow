"""WebSocket endpoints for real-time task updates."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, Query
from typing import Annotated

from mindflow_backend.api.websocket.task_updates import (
    TaskUpdateSubscription,
    TaskUpdateWebSocketManager,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/tasks/updates")
async def task_updates_websocket(
    websocket: WebSocket,
    task_list_id: Annotated[str | None, Query()] = None,
    session_id: Annotated[str | None, Query()] = None,
    owner: Annotated[str | None, Query()] = None,
) -> None:
    """WebSocket endpoint for real-time task updates.

    Clients can subscribe to task updates with optional filters:
    - task_list_id: Only receive updates for tasks in this list
    - session_id: Only receive updates for tasks in this session
    - owner: Only receive updates for tasks owned by this user/agent

    Example connection:
        ws://localhost:8000/ws/tasks/updates?task_list_id=session_123

    Message format (sent to client):
        {
            "event_type": "task_created" | "task_updated" | "task_completed",
            "task_id": 1,
            "task_list_id": "session_123",
            "subject": "Task subject",
            "status": "pending",
            "owner": "agent_name",
            "session_id": "session_123",
            "timestamp": "2026-04-03T17:00:00Z"
        }

    Client can update subscription by sending:
        {
            "type": "update_subscription",
            "subscription": {
                "task_list_id": "new_list_id",
                "session_id": "new_session_id",
                "owner": "new_owner"
            }
        }
    """
    subscription = TaskUpdateSubscription(
        task_list_id=task_list_id,
        session_id=session_id,
        owner=owner,
    )

    manager = await TaskUpdateWebSocketManager.get_instance()
    await manager.handle_connection(websocket, subscription)
