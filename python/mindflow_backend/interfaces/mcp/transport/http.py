"""
HTTP MCP Transport Implementation

Transport implementation for MCP communication over HTTP/HTTPS.
Suitable for web-based MCP servers and REST API integration.
"""

import asyncio
import json
import ssl
from typing import Optional, Dict, Any
import logging

try:
    import aiohttp
    from aiohttp import ClientSession, ClientTimeout, ClientError
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None
    ClientSession = None
    ClientTimeout = None
    ClientError = None

from mindflow_backend.interfaces.mcp.transport.base import (
    MCPTransport, TransportState, TransportError, ConnectionError, MessageError
)
from mindflow_backend.schemas.mcp.base import MCPMessage
from mindflow_backend.schemas.mcp.transport import HTTPConfig


class HTTPTransportError(TransportError):
    """Exception specific to HTTP transport errors."""
    pass


class HTTPTransport(MCPTransport):
    """
    MCP transport implementation using HTTP/HTTPS.
    
    This transport is suitable for web-based MCP servers and provides
    reliable communication over HTTP with proper error handling and retries.
    """
    
    def __init__(self, config: HTTPConfig):
        """
        Initialize HTTP transport.
        
        Args:
            config: HTTP transport configuration
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for HTTP transport. Install with: pip install aiohttp")
        
        super().__init__(config)
        self.session: Optional[ClientSession] = None
        self._request_id_counter = 0
        self._pending_requests: Dict[str, asyncio.Future] = {}
    
    async def connect(self) -> None:
        """
        Initialize HTTP session and test connectivity.
        
        Raises:
            ConnectionError: If connection fails
        """
        if self.state != TransportState.DISCONNECTED:
            raise ConnectionError(f"Cannot connect from state {self.state}")
        
        self._set_state(TransportState.CONNECTING)
        
        try:
            # Create SSL context
            ssl_context = None
            if not self.config.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create session with timeout
            timeout = ClientTimeout(total=self.config.timeout)
            
            # Initialize session
            self.session = ClientSession(
                timeout=timeout,
                headers=self.config.headers,
                connector=aiohttp.TCPConnector(
                    verify_ssl=self.config.verify_ssl,
                    ssl=ssl_context,
                )
            )
            
            # Test connectivity with a simple request
            await self._test_connection()
            
            self._set_state(TransportState.CONNECTED)
            self._connection_info = {
                "url": self.config.url,
                "method": self.config.method,
                "verify_ssl": self.config.verify_ssl,
                "headers": self.config.headers,
            }
            
            self.logger.info(f"HTTP transport connected to {self.config.url}")
            
        except Exception as e:
            self._set_state(TransportState.ERROR)
            await self._cleanup()
            raise ConnectionError(f"Failed to connect HTTP transport: {e}")
    
    async def disconnect(self) -> None:
        """Close HTTP session and cleanup resources."""
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
        
        self.logger.info("HTTP transport disconnected")
    
    async def send_message(self, message: MCPMessage) -> None:
        """
        Send a message via HTTP POST request.
        
        Args:
            message: The message to send
            
        Raises:
            MessageError: If sending fails
        """
        if not self.is_connected or not self.session:
            raise ConnectionError("Transport is not connected")
        
        try:
            # Prepare request data
            message_json = message.model_dump_json(exclude_none=True)
            headers = {
                "Content-Type": "application/json",
                **self.config.headers
            }
            
            # Send HTTP request
            async with self.session.request(
                method=self.config.method,
                url=self.config.url,
                data=message_json,
                headers=headers,
                allow_redirects=self.config.follow_redirects,
                max_redirects=self.config.max_redirects
            ) as response:
                
                # Handle response
                if response.status >= 400:
                    error_text = await response.text()
                    raise MessageError(
                        f"HTTP error {response.status}: {error_text}"
                    )
                
                # For HTTP transport, we don't expect an immediate response
                # The response will come through a separate receive_message call
                # or via webhook/long polling if implemented
                
                response_text = await response.text()
                if response_text:
                    try:
                        # If there's an immediate response, parse it
                        response_data = json.loads(response_text)
                        response_message = MCPMessage.model_validate(response_data)
                        
                        # Store response for matching with request ID
                        if message.id and response_message.id == message.id:
                            if message.id in self._pending_requests:
                                self._pending_requests[message.id].set_result(response_message)
                                del self._pending_requests[message.id]
                        
                    except (json.JSONDecodeError, Exception):
                        # Ignore invalid response for now
                        pass
                
                self._update_metrics("sent", len(message_json.encode()))
                self.logger.debug(f"Sent HTTP message: {message_json[:100]}...")
                
        except ClientError as e:
            self._update_metrics("error")
            raise MessageError(f"HTTP client error: {e}")
        except Exception as e:
            self._update_metrics("error")
            raise MessageError(f"Failed to send HTTP message: {e}")
    
    async def receive_message(self) -> Optional[MCPMessage]:
        """
        Receive a message via HTTP.
        
        For basic HTTP transport, this method might not be applicable
        as HTTP is request-response. This could be implemented with:
        - Long polling
        - Webhooks
        - Server-sent events
        
        Returns:
            Optional[MCPMessage]: Received message or None
            
        Raises:
            MessageError: If receiving fails
        """
        # For basic HTTP transport, we don't have a way to receive messages
        # This would need to be implemented with long polling or webhooks
        return None
    
    async def send_and_wait(self, message: MCPMessage, timeout: Optional[float] = None) -> MCPMessage:
        """
        Send a message and wait for response using HTTP.
        
        Args:
            message: The message to send
            timeout: Optional timeout in seconds
            
        Returns:
            MCPMessage: The response message
            
        Raises:
            TimeoutError: If no response within timeout
        """
        if not self.is_connected or not self.session:
            raise ConnectionError("Transport is not connected")
        
        # Ensure message has an ID
        if not message.id:
            self._request_id_counter += 1
            message.id = f"http_req_{self._request_id_counter}"
        
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
    
    async def _test_connection(self) -> None:
        """
        Test HTTP connectivity with a simple request.
        
        Raises:
            ConnectionError: If connection test fails
        """
        try:
            # Send a simple OPTIONS or HEAD request to test connectivity
            async with self.session.request(
                method="OPTIONS",
                url=self.config.url,
                headers=self.config.headers
            ) as response:
                # Accept any response that indicates server is reachable
                if response.status not in [200, 204, 405]:  # 405 Method Not Allowed is OK
                    raise ConnectionError(
                        f"Connection test failed with status {response.status}"
                    )
                    
        except ClientError as e:
            raise ConnectionError(f"HTTP connection test failed: {e}")
    
    async def _cleanup(self) -> None:
        """Cleanup HTTP session and related resources."""
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                self.logger.error(f"Error closing HTTP session: {e}")
            finally:
                self.session = None
