"""
MCP Message Handlers

Base interfaces and implementations for handling MCP protocol messages.
Provides the foundation for processing requests, responses, and notifications.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Awaitable

from mindflow_backend.schemas.mcp.base import MCPMessage, MCPRequest, MCPResponse


class BaseMessageHandler(ABC):
    """
    Abstract base class for MCP message handlers.
    
    All message handlers should inherit from this class and implement
    the handle_message method for processing specific message types.
    """
    
    def __init__(self):
        """Initialize the message handler."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def handle_message(self, message: MCPMessage) -> Optional[MCPResponse]:
        """
        Handle an incoming MCP message.
        
        Args:
            message: The incoming MCP message
            
        Returns:
            Optional[MCPResponse]: Response message if needed, None otherwise
        """
        pass
    
    def can_handle(self, message: MCPMessage) -> bool:
        """
        Check if this handler can process the given message.
        
        Args:
            message: The message to check
            
        Returns:
            bool: True if this handler can process the message
        """
        return True


class MCPMessageHandler:
    """
    Composite message handler that routes messages to appropriate handlers.
    
    This handler manages multiple specialized handlers and routes incoming
    messages to the correct handler based on message type and content.
    """
    
    def __init__(self):
        """Initialize the message handler."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._handlers: List[BaseMessageHandler] = []
        self._middleware: List[Callable[[MCPMessage], Awaitable[bool]]] = []
        self._error_handler: Optional[Callable[[Exception, MCPMessage], Awaitable[None]]] = None
    
    def add_handler(self, handler: BaseMessageHandler) -> None:
        """
        Add a message handler.
        
        Args:
            handler: The handler to add
        """
        self._handlers.append(handler)
        self.logger.debug(f"Added handler: {handler.__class__.__name__}")
    
    def remove_handler(self, handler: BaseMessageHandler) -> None:
        """
        Remove a message handler.
        
        Args:
            handler: The handler to remove
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            self.logger.debug(f"Removed handler: {handler.__class__.__name__}")
    
    def add_middleware(self, middleware: Callable[[MCPMessage], Awaitable[bool]]) -> None:
        """
        Add middleware for message processing.
        
        Args:
            middleware: Middleware function that returns True to continue processing
        """
        self._middleware.append(middleware)
        self.logger.debug("Added middleware")
    
    def set_error_handler(self, handler: Callable[[Exception, MCPMessage], Awaitable[None]]) -> None:
        """
        Set error handler for message processing.
        
        Args:
            handler: Error handler function
        """
        self._error_handler = handler
    
    async def handle_message(self, message: MCPMessage) -> Optional[MCPResponse]:
        """
        Handle an incoming message by routing to appropriate handlers.
        
        Args:
            message: The incoming message
            
        Returns:
            Optional[MCPResponse]: Response message if needed
        """
        try:
            # Apply middleware
            for middleware in self._middleware:
                try:
                    should_continue = await middleware(message)
                    if not should_continue:
                        self.logger.debug("Middleware stopped message processing")
                        return None
                except Exception as e:
                    self.logger.error(f"Middleware error: {e}")
                    if self._error_handler:
                        await self._error_handler(e, message)
                    return None
            
            # Find appropriate handler
            for handler in self._handlers:
                if handler.can_handle(message):
                    try:
                        response = await handler.handle_message(message)
                        if response:
                            self.logger.debug(f"Handler {handler.__class__.__name__} produced response")
                        return response
                    except Exception as e:
                        self.logger.error(f"Handler {handler.__class__.__name__} error: {e}")
                        if self._error_handler:
                            await self._error_handler(e, message)
                        # Continue to next handler
            
            # No handler could process the message
            self.logger.warning(f"No handler found for message: {message.method}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}")
            if self._error_handler:
                await self._error_handler(e, message)
            return None


class RequestHandler(BaseMessageHandler):
    """
    Base handler for MCP request messages.
    
    This handler provides common functionality for processing request messages
    and can be extended for specific request types.
    """
    
    def __init__(self, supported_methods: Optional[List[str]] = None):
        """
        Initialize request handler.
        
        Args:
            supported_methods: List of supported method names
        """
        super().__init__()
        self.supported_methods = supported_methods or []
    
    def can_handle(self, message: MCPMessage) -> bool:
        """Check if this handler can process the request."""
        if not isinstance(message, MCPRequest) and not message.method:
            return False
        
        if self.supported_methods:
            return message.method in self.supported_methods
        
        return True
    
    async def handle_message(self, message: MCPMessage) -> Optional[MCPResponse]:
        """Handle the request message."""
        if not self.can_handle(message):
            return None
        
        return await self.handle_request(message)
    
    @abstractmethod
    async def handle_request(self, message: MCPMessage) -> Optional[MCPResponse]:
        """
        Handle the specific request.
        
        Args:
            message: The request message
            
        Returns:
            Optional[MCPResponse]: Response message
        """
        pass


class NotificationHandler(BaseMessageHandler):
    """
    Base handler for MCP notification messages.
    
    This handler processes notification messages (messages without an ID)
    which don't require responses.
    """
    
    def can_handle(self, message: MCPMessage) -> bool:
        """Check if this is a notification message."""
        return message.method is not None and message.id is None
    
    async def handle_message(self, message: MCPMessage) -> Optional[MCPResponse]:
        """Handle the notification message."""
        if not self.can_handle(message):
            return None
        
        await self.handle_notification(message)
        return None  # Notifications don't require responses
    
    @abstractmethod
    async def handle_notification(self, message: MCPMessage) -> None:
        """
        Handle the specific notification.
        
        Args:
            message: The notification message
        """
        pass


class ResponseHandler(BaseMessageHandler):
    """
    Base handler for MCP response messages.
    
    This handler processes response messages and can be used for
    tracking request-response pairs or handling errors.
    """
    
    def can_handle(self, message: MCPMessage) -> bool:
        """Check if this is a response message."""
        return (message.result is not None or message.error is not None) and message.id is not None
    
    async def handle_message(self, message: MCPMessage) -> Optional[MCPResponse]:
        """Handle the response message."""
        if not self.can_handle(message):
            return None
        
        await self.handle_response(message)
        return None  # Responses don't require further responses
    
    @abstractmethod
    async def handle_response(self, message: MCPMessage) -> None:
        """
        Handle the specific response.
        
        Args:
            message: The response message
        """
        pass


class LoggingMiddleware:
    """
    Middleware for logging MCP messages.
    
    This middleware logs incoming and outgoing messages for debugging
    and monitoring purposes.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize logging middleware.
        
        Args:
            logger: Logger instance (creates default if None)
        """
        self.logger = logger or logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def __call__(self, message: MCPMessage) -> bool:
        """
        Log the message and continue processing.
        
        Args:
            message: The message to log
            
        Returns:
            bool: True to continue processing
        """
        if message.method:
            if message.id:
                self.logger.info(f"Request: {message.method} (ID: {message.id})")
            else:
                self.logger.info(f"Notification: {message.method}")
        elif message.result is not None:
            self.logger.info(f"Response: {message.id}")
        elif message.error is not None:
            self.logger.warning(f"Error Response: {message.id} - {message.error.message}")
        
        return True


class AuthenticationMiddleware:
    """
    Middleware for authenticating MCP messages.
    
    This middleware checks authentication tokens or credentials
    before allowing message processing to continue.
    """
    
    def __init__(self, auth_token: str, token_header: str = "Authorization"):
        """
        Initialize authentication middleware.
        
        Args:
            auth_token: Expected authentication token
            token_header: Header name containing the token
        """
        self.auth_token = auth_token
        self.token_header = token_header
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def __call__(self, message: MCPMessage) -> bool:
        """
        Check authentication and continue if valid.
        
        Args:
            message: The message to authenticate
            
        Returns:
            bool: True if authenticated, False otherwise
        """
        # This is a simplified example - in practice, you'd extract
        # the token from message headers or metadata
        message_token = getattr(message, 'auth_token', None)
        
        if message_token == self.auth_token:
            return True
        
        self.logger.warning("Authentication failed")
        return False
