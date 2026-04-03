"""WebSocket manager for real-time task updates.

Manages WebSocket connections and broadcasts task lifecycle events
(created, updated, completed) to subscribed clients.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class TaskUpdateSubscription(BaseModel):
    """Subscription filter for task updates."""

    task_list_id: str | None = None
    session_id: str | None = None
    owner: str | None = None


class TaskUpdateMessage(BaseModel):
    """Message sent to WebSocket clients for task updates."""

    event_type: str = Field(..., description="Type of event: task_created, task_updated, task_completed")
    task_id: int = Field(..., description="ID of the task")
    task_list_id: str = Field(..., description="Task list ID")
    subject: str = Field(..., description="Task subject")
    status: str = Field(..., description="Current task status")
    owner: str | None = Field(None, description="Task owner")
    session_id: str | None = Field(None, description="Associated session ID")
    timestamp: str = Field(..., description="ISO timestamp of the event")


class WebSocketConnection:
    """Represents a single WebSocket connection with its subscription filters."""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        subscription: TaskUpdateSubscription,
    ) -> None:
        self.websocket = websocket
        self.connection_id = connection_id
        self.subscription = subscription
        self.is_active = True

    def matches_filter(self, message: TaskUpdateMessage) -> bool:
        """Check if message matches this connection's subscription filters.

        Args:
            message: Task update message to check

        Returns:
            True if message matches filters, False otherwise
        """
        # If no filters set, receive all messages
        if (
            self.subscription.task_list_id is None
            and self.subscription.session_id is None
            and self.subscription.owner is None
        ):
            return True

        # Check task_list_id filter
        if self.subscription.task_list_id and message.task_list_id != self.subscription.task_list_id:
            return False

        # Check session_id filter
        if self.subscription.session_id and message.session_id != self.subscription.session_id:
            return False

        # Check owner filter
        if self.subscription.owner and message.owner != self.subscription.owner:
            return False

        return True

    async def send_message(self, message: TaskUpdateMessage) -> bool:
        """Send message to this connection.

        Args:
            message: Message to send

        Returns:
            True if sent successfully, False if connection is closed
        """
        if not self.is_active:
            return False

        try:
            await self.websocket.send_json(message.model_dump())
            return True
        except Exception as e:
            _logger.warning(
                "websocket_send_failed",
                connection_id=self.connection_id,
                error=str(e),
            )
            self.is_active = False
            return False


class TaskUpdateWebSocketManager:
    """Manages WebSocket connections for task updates.

    Singleton manager that handles:
    - Connection registration and cleanup
    - Message broadcasting with filtering
    - Connection health monitoring
    """

    _instance: TaskUpdateWebSocketManager | None = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        self._connections: dict[str, WebSocketConnection] = {}
        self._broadcast_queue: asyncio.Queue[TaskUpdateMessage] = asyncio.Queue()
        self._broadcast_task: asyncio.Task | None = None

    @classmethod
    async def get_instance(cls) -> TaskUpdateWebSocketManager:
        """Get singleton instance of the manager."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._start_broadcast_worker()
        return cls._instance

    async def _start_broadcast_worker(self) -> None:
        """Start background worker for broadcasting messages."""
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_worker())
            _logger.info("task_update_broadcast_worker_started")

    async def _broadcast_worker(self) -> None:
        """Background worker that processes broadcast queue."""
        while True:
            try:
                message = await self._broadcast_queue.get()
                await self._broadcast_to_connections(message)
            except Exception as e:
                _logger.error(
                    "broadcast_worker_error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(1)  # Prevent tight loop on errors

    async def _broadcast_to_connections(self, message: TaskUpdateMessage) -> None:
        """Broadcast message to all matching connections.

        Args:
            message: Message to broadcast
        """
        sent_count = 0
        failed_connections = []

        for connection_id, connection in self._connections.items():
            if connection.matches_filter(message):
                success = await connection.send_message(message)
                if success:
                    sent_count += 1
                else:
                    failed_connections.append(connection_id)

        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        _logger.debug(
            "task_update_broadcast",
            event_type=message.event_type,
            task_id=message.task_id,
            sent_count=sent_count,
            failed_count=len(failed_connections),
        )

    async def connect(
        self,
        websocket: WebSocket,
        subscription: TaskUpdateSubscription,
    ) -> str:
        """Register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            subscription: Subscription filters

        Returns:
            Connection ID
        """
        await websocket.accept()

        connection_id = str(uuid4())
        connection = WebSocketConnection(websocket, connection_id, subscription)
        self._connections[connection_id] = connection

        _logger.info(
            "websocket_connected",
            connection_id=connection_id,
            subscription=subscription.model_dump(),
            total_connections=len(self._connections),
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Disconnect and remove a WebSocket connection.

        Args:
            connection_id: ID of connection to remove
        """
        if connection_id in self._connections:
            connection = self._connections[connection_id]
            connection.is_active = False
            del self._connections[connection_id]

            _logger.info(
                "websocket_disconnected",
                connection_id=connection_id,
                total_connections=len(self._connections),
            )

    async def broadcast_task_update(self, message: TaskUpdateMessage) -> None:
        """Queue a task update message for broadcasting.

        Args:
            message: Message to broadcast
        """
        await self._broadcast_queue.put(message)

    async def handle_connection(
        self,
        websocket: WebSocket,
        subscription: TaskUpdateSubscription,
    ) -> None:
        """Handle a WebSocket connection lifecycle.

        Args:
            websocket: WebSocket connection
            subscription: Subscription filters
        """
        connection_id = await self.connect(websocket, subscription)

        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for client messages (ping/pong, subscription updates)
                data = await websocket.receive_json()

                # Handle subscription updates
                if data.get("type") == "update_subscription":
                    new_subscription = TaskUpdateSubscription(**data.get("subscription", {}))
                    if connection_id in self._connections:
                        self._connections[connection_id].subscription = new_subscription
                        _logger.info(
                            "subscription_updated",
                            connection_id=connection_id,
                            subscription=new_subscription.model_dump(),
                        )

        except WebSocketDisconnect:
            _logger.info("websocket_client_disconnected", connection_id=connection_id)
        except Exception as e:
            _logger.error(
                "websocket_connection_error",
                connection_id=connection_id,
                error=str(e),
                exc_info=True,
            )
        finally:
            await self.disconnect(connection_id)

    def get_connection_count(self) -> int:
        """Get number of active connections.

        Returns:
            Number of active connections
        """
        return len(self._connections)
