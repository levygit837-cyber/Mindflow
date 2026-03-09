"""
WebSocket MCP Transport Implementation

Transport implementation for MCP communication over WebSocket.
Suitable for real-time bidirectional communication with MCP servers.
"""

import asyncio
import json
import ssl
from typing import Optional, Dict, Any
import logging

try:
    import websockets
    from websockets.asyncio.client import ClientConnection
    from websockets.exceptions import ConnectionClosed, WebSocketException
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None
    ClientConnection = None
    ConnectionClosed = None
    WebSocketException = None

from mindflow_backend.interfaces.mcp.transport.base import (
    MCPTransport, TransportState, TransportError, ConnectionError, MessageError
)
from mindflow_backend.schemas.mcp.base import MCPMessage
from mindflow_backend.schemas.mcp.transport import WebSocketConfig


class WebSocketTransportError(TransportError):
    """Exception specific to WebSocket transport errors."""
    pass


class WebSocketTransport(MCPTransport):
    """
    MCP transport implementation using WebSocket.
    
    This transport provides real-time bidirectional communication with MCP servers
    and is suitable for interactive applications requiring low latency.
    """
    
    def __init__(self, config: WebSocketConfig):
        """
        Initialize WebSocket transport.
        
        Args:
            config: WebSocket transport configuration
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets is required for WebSocket transport. Install with: pip install websockets")
        
        super().__init__(config)
        self.connection: Optional[ClientConnection] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._listener_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._request_id_counter = 0
        self._pending_requests: Dict[str, asyncio.Future] = {}
    
    async def connect(self) -> None:
        """
        Establish WebSocket connection.
        
        Raises:
            ConnectionError: If connection fails
        """
        if self.state != TransportState.DISCONNECTED:
            raise ConnectionError(f"Cannot connect from state {self.state}")
        
        self._set_state(TransportState.CONNECTING)
        
        try:
            # Create SSL context if needed
            ssl_context = None
            if self.config.url.startswith("wss://"):
                ssl_context = ssl.create_default_context()
            
            # Set up extra headers
            extra_headers = self.config.headers.copy()
            if self.config.origin:
                extra_headers["Origin"] = self.config.origin
            
            # Connect to WebSocket
            self.connection = await websockets.connect(
                self.config.url,
                subprotocols=self.config.subprotocols,
                extra_headers=extra_headers,
                ssl=ssl_context,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                close_timeout=self.config.close_timeout,
                max_size=self.config.max_size,
                max_queue=self.config.max_queue,
            )
            
            # Start listener task
            self._listener_task = asyncio.create_task(self._message_listener())
            
            # Start ping task if configured
            if self.config.ping_interval > 0:
                self._ping_task = asyncio.create_task(self._ping_sender())
            
            self._set_state(TransportState.CONNECTED)
            self._connection_info = {
                "url": self.config.url,
                "subprotocols": self.config.subprotocols,
                "origin": self.config.origin,
                "local_address": str(self.connection.local_address),
                "remote_address": str(self.connection.remote_address),
            }
            
            self.logger.info(f"WebSocket transport connected to {self.config.url}")
            
        except Exception as e:
            self._set_state(TransportState.ERROR)
            await self._cleanup()
            raise ConnectionError(f"Failed to connect WebSocket transport: {e}")
    
    async def disconnect(self) -> None:
        """Close WebSocket connection and cleanup resources."""
        if self.state == TransportState.DISCONNECTED:
            return
        
        self._set_state(TransportState.CLOSING)
        
        # Cancel all pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        
        await self._cleanup()
        self._set_state(TransportState.DISCONNECTED)
        
        self.logger.info("WebSocket transport disconnected")
    
    async def send_message(self, message: MCPMessage) -> None:
        """
        Send a message via WebSocket.
        
        Args:
            message: The message to send
            
        Raises:
            MessageError: If sending fails
        """
        if not self.is_connected or not self.connection:
            raise ConnectionError("Transport is not connected")
        
        try:
            # Serialize message to JSON
            message_json = message.model_dump_json(exclude_none=True)
            
            # Send message
            await self.connection.send(message_json)
            
            self._update_metrics("sent", len(message_json.encode()))
            self.logger.debug(f"Sent WebSocket message: {message_json[:100]}...")
            
        except ConnectionClosed:
            await self._handle_connection_closed()
            raise ConnectionError("WebSocket connection closed")
        except WebSocketException as e:
            self._update_metrics("error")
            raise MessageError(f"WebSocket error: {e}")
        except Exception as e:
            self._update_metrics("error")
            raise MessageError(f"Failed to send WebSocket message: {e}")
    
    async def receive_message(self) -> Optional[MCPMessage]:
        """
        Receive a message from WebSocket queue.
        
        Returns:
            Optional[MCPMessage]: Received message or None if no message available
            
        Raises:
            MessageError: If receiving fails
        """
        try:
            # Get message from queue (non-blocking)
            message_json = self._message_queue.get_nowait()
            
            # Parse JSON message
            try:
                message_data = json.loads(message_json)
                message = MCPMessage.model_validate(message_data)
            except json.JSONDecodeError as e:
                raise MessageError(f"Invalid JSON received: {e}")
            except Exception as e:
                raise MessageError(f"Invalid message format: {e}")
            
            self._update_metrics("received", len(message_json.encode()))
            self.logger.debug(f"Received WebSocket message: {message_json[:100]}...")
            
            return message
            
        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            self._update_metrics("error")
            raise MessageError(f"Failed to receive WebSocket message: {e}")
    
    async def send_and_wait(self, message: MCPMessage, timeout: Optional[float] = None) -> MCPMessage:
        """
        Send a message and wait for response using WebSocket.
        
        Args:
            message: The message to send
            timeout: Optional timeout in seconds
            
        Returns:
            MCPMessage: The response message
            
        Raises:
            TimeoutError: If no response within timeout
        """
        if not self.is_connected or not self.connection:
            raise ConnectionError("Transport is not connected")
        
        # Ensure message has an ID
        if not message.id:
            self._request_id_counter += 1
            message.id = f"ws_req_{self._request_id_counter}"
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_requests[message.id] = response_future
        
        try:
            # Send the message
            await self.send_message(message)
            
            # Wait for response
            if timeout:
                await asyncio.wait_for(response_future, timeout=timeout)
            else:
                await response_future
            
            return response_future.result()
            
        except asyncio.TimeoutError:
            # Clean up pending request
            if message.id in self._pending_requests:
                del self._pending_requests[message.id]
            raise TimeoutError(f"Timeout waiting for response to message {message.id}")
        except Exception as e:
            # Clean up pending request
            if message.id in self._pending_requests:
                del self._pending_requests[message.id]
            raise
    
    async def _message_listener(self) -> None:
        """
        Listen for incoming WebSocket messages.
        """
        if not self.connection:
            return
        
        try:
            async for message in self.connection:
                try:
                    message_str = message if isinstance(message, str) else message.decode()
                    
                    # Parse message to check for request ID
                    try:
                        message_data = json.loads(message_str)
                        request_id = message_data.get("id")
                        
                        # If this is a response to a pending request, resolve the future
                        if request_id and request_id in self._pending_requests:
                            try:
                                response_message = MCPMessage.model_validate(message_data)
                                self._pending_requests[request_id].set_result(response_message)
                                del self._pending_requests[request_id]
                                continue
                            except Exception as e:
                                # If parsing fails, still put in queue for handler
                                pass
                    
                    except json.JSONDecodeError:
                        # Invalid JSON, put raw message in queue
                        pass
                    
                    # Put message in queue for general handling
                    await self._message_queue.put(message_str)
                    
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")
                    
        except ConnectionClosed:
            await self._handle_connection_closed()
        except Exception as e:
            self.logger.error(f"WebSocket listener error: {e}")
    
    async def _ping_sender(self) -> None:
        """
        Send periodic pings to keep connection alive.
        """
        if not self.connection:
            return
        
        try:
            while self.is_connected:
                await asyncio.sleep(self.config.ping_interval)
                
                if self.is_connected and self.connection:
                    try:
                        await self.connection.ping()
                    except Exception as e:
                        self.logger.error(f"Ping failed: {e}")
                        break
                        
        except Exception as e:
            self.logger.error(f"Ping sender error: {e}")
    
    async def _handle_connection_closed(self) -> None:
        """Handle unexpected connection closure."""
        self._set_state(TransportState.ERROR)
        
        # Cancel all pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(ConnectionError("WebSocket connection closed"))
        self._pending_requests.clear()
        
        self.logger.warning("WebSocket connection closed unexpectedly")
    
    async def _cleanup(self) -> None:
        """Cleanup WebSocket connection and related resources."""
        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        
        # Cancel ping task
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None
        
        # Close WebSocket connection
        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket connection: {e}")
            finally:
                self.connection = None
        
        # Clear message queue
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
