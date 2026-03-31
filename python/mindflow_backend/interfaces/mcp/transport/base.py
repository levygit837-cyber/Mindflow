"""
Base MCP Transport Interface

Abstract base class and common utilities for all MCP transport implementations.
Provides the foundation for stdio, HTTP, and WebSocket transports.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import Enum
from typing import Any

from mindflow_backend.schemas.mcp.base import MCPMessage
from mindflow_backend.schemas.mcp.transport import MCPTransportConfig


class TransportState(str, Enum):
    """Transport connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    CLOSING = "closing"


class TransportError(Exception):
    """Base exception for transport-related errors."""
    pass


class ConnectionError(TransportError):
    """Exception for connection-related errors."""
    pass


class MessageError(TransportError):
    """Exception for message-related errors."""
    pass


class TimeoutError(TransportError):
    """Exception for timeout-related errors."""
    pass


class MCPTransport(ABC):
    """
    Abstract base class for MCP transport implementations.
    
    All transport implementations must inherit from this class and implement
    the abstract methods for connecting, sending, receiving, and disconnecting.
    """
    
    def __init__(self, config: MCPTransportConfig):
        """
        Initialize the transport with configuration.
        
        Args:
            config: Transport configuration
        """
        self.config = config
        self.state = TransportState.DISCONNECTED
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._message_handler: Callable[[MCPMessage], Awaitable[None]] | None = None
        self._error_handler: Callable[[Exception], Awaitable[None]] | None = None
        self._connection_info: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {
            "messages_sent": 0,
            "messages_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "errors": 0,
            "connection_attempts": 0,
            "last_activity": None,
            "connected_at": None,
        }
    
    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self.state == TransportState.CONNECTED
    
    @property
    def is_disconnected(self) -> bool:
        """Check if transport is disconnected."""
        return self.state == TransportState.DISCONNECTED
    
    @property
    def connection_info(self) -> dict[str, Any]:
        """Get connection information."""
        return self._connection_info.copy()
    
    @property
    def metrics(self) -> dict[str, Any]:
        """Get transport metrics."""
        metrics = self._metrics.copy()
        if metrics["connected_at"]:
            uptime = (datetime.utcnow() - datetime.fromisoformat(metrics["connected_at"])).total_seconds()
            metrics["uptime"] = uptime
        return metrics
    
    def set_message_handler(self, handler: Callable[[MCPMessage], Awaitable[None]]) -> None:
        """
        Set the message handler for incoming messages.
        
        Args:
            handler: Async function to handle incoming messages
        """
        self._message_handler = handler
    
    def set_error_handler(self, handler: Callable[[Exception], Awaitable[None]]) -> None:
        """
        Set the error handler for transport errors.
        
        Args:
            handler: Async function to handle errors
        """
        self._error_handler = handler
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection using the configured transport.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close the connection and cleanup resources.
        """
        pass
    
    @abstractmethod
    async def send_message(self, message: MCPMessage) -> None:
        """
        Send a message through the transport.
        
        Args:
            message: The message to send
            
        Raises:
            MessageError: If sending fails
        """
        pass
    
    @abstractmethod
    async def receive_message(self) -> MCPMessage | None:
        """
        Receive a message from the transport.
        
        Returns:
            Optional[MCPMessage]: Received message or None if no message available
            
        Raises:
            MessageError: If receiving fails
        """
        pass
    
    async def send_and_wait(self, message: MCPMessage, timeout: float | None = None) -> MCPMessage:
        """
        Send a message and wait for response.
        
        Args:
            message: The message to send
            timeout: Optional timeout in seconds
            
        Returns:
            MCPMessage: The response message
            
        Raises:
            TimeoutError: If no response within timeout
        """
        if not self.is_connected:
            raise ConnectionError("Transport is not connected")
        
        # Store the message ID for response matching
        message_id = message.id
        
        # Send the message
        await self.send_message(message)
        
        # Wait for response with matching ID
        start_time = asyncio.get_event_loop().time()
        while True:
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                raise TimeoutError(f"Timeout waiting for response to message {message_id}")
            
            response = await self.receive_message()
            if response and response.id == message_id:
                return response
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.01)
    
    async def start_listening(self) -> None:
        """
        Start listening for incoming messages.
        This method should be called after connect().
        """
        if not self.is_connected:
            raise ConnectionError("Transport is not connected")
        
        self.logger.info("Starting to listen for incoming messages")
        
        try:
            while self.is_connected:
                try:
                    message = await self.receive_message()
                    if message and self._message_handler:
                        await self._message_handler(message)
                except Exception as e:
                    self._metrics["errors"] += 1
                    if self._error_handler:
                        await self._error_handler(e)
                    else:
                        self.logger.error(f"Error in message listener: {e}")
                        break
        except asyncio.CancelledError:
            self.logger.info("Message listener cancelled")
        except Exception as e:
            self.logger.error(f"Unexpected error in message listener: {e}")
            raise
    
    def _update_metrics(self, operation: str, bytes_count: int = 0) -> None:
        """
        Update transport metrics.
        
        Args:
            operation: Type of operation (sent, received, error)
            bytes_count: Number of bytes transferred
        """
        self._metrics["last_activity"] = datetime.utcnow().isoformat()
        
        if operation == "sent":
            self._metrics["messages_sent"] += 1
            self._metrics["bytes_sent"] += bytes_count
        elif operation == "received":
            self._metrics["messages_received"] += 1
            self._metrics["bytes_received"] += bytes_count
        elif operation == "error":
            self._metrics["errors"] += 1
    
    def _set_state(self, state: TransportState) -> None:
        """
        Update transport state.
        
        Args:
            state: New transport state
        """
        old_state = self.state
        self.state = state
        self.logger.debug(f"Transport state changed from {old_state} to {state}")
        
        if state == TransportState.CONNECTED:
            self._metrics["connected_at"] = datetime.utcnow().isoformat()
        elif state == TransportState.CONNECTING:
            self._metrics["connection_attempts"] += 1
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
