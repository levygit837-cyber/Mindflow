"""
P2P Protocol for MindFlow agent communication.

Adapted from Plexo project for MindFlow architecture.
Provides peer-to-peer messaging between agents.
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """P2P message types."""
    DIRECT = "direct"
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    URGENT = "urgent"


@dataclass
class P2PMessage:
    """Peer-to-peer message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    content: str = ""
    message_type: MessageType = MessageType.DIRECT
    urgency: str = "MEDIUM"
    requires_response: bool = False
    in_reply_to: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content": self.content,
            "message_type": self.message_type.value,
            "urgency": self.urgency,
            "requires_response": self.requires_response,
            "in_reply_to": self.in_reply_to,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'P2PMessage':
        """Create instance from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            content=data.get("content", ""),
            message_type=MessageType(data.get("message_type", "direct")),
            urgency=data.get("urgency", "MEDIUM"),
            requires_response=data.get("requires_response", False),
            in_reply_to=data.get("in_reply_to"),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            metadata=data.get("metadata", {})
        )


class P2PProtocol:
    """
    Peer-to-peer communication protocol.
    
    Enables direct messaging between MindFlow agents
    with support for requests, responses, and notifications.
    """
    
    def __init__(self, agent_id: str, connection_manager: Any):
        self.agent_id = agent_id
        self.connection_manager = connection_manager
        self.pending_requests: dict[str, P2PMessage] = {}
        self.message_history: list[P2PMessage] = []
        self.response_handlers: dict[str, Callable] = {}
        self.is_listening: bool = False
    
    async def send_direct_message(
        self,
        to_agent: str,
        content: str,
        urgency: str = "MEDIUM"
    ) -> dict[str, Any]:
        """
        Send a direct message to another agent.
        
        Args:
            to_agent: Recipient agent ID
            content: Message content
            urgency: Message urgency level
            
        Returns:
            Send result dictionary
        """
        message = P2PMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.DIRECT,
            urgency=urgency
        )
        
        result = await self.connection_manager.send_message(
            from_username=self.agent_id,
            to_username=to_agent,
            content=content,
            urgency=urgency
        )
        
        if result.get("success"):
            self.message_history.append(message)
            logger.info(f"Direct message sent from {self.agent_id} to {to_agent}")
        
        return result
    
    async def send_request(
        self,
        to_agent: str,
        content: str,
        urgency: str = "HIGH"
    ) -> dict[str, Any]:
        """
        Send a request that requires a response.
        
        Args:
            to_agent: Recipient agent ID
            content: Request content
            urgency: Message urgency level
            
        Returns:
            Send result dictionary
        """
        message = P2PMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.REQUEST,
            urgency=urgency,
            requires_response=True
        )
        
        self.pending_requests[message.message_id] = message
        
        result = await self.connection_manager.send_message(
            from_username=self.agent_id,
            to_username=to_agent,
            content=content,
            urgency=urgency
        )
        
        if result.get("success"):
            self.message_history.append(message)
            logger.info(f"Request sent from {self.agent_id} to {to_agent}")
        
        return result
    
    async def send_response(
        self,
        to_agent: str,
        original_message_id: str,
        content: str
    ) -> dict[str, Any]:
        """
        Send a response to a request.
        
        Args:
            to_agent: Recipient agent ID
            original_message_id: ID of the message being replied to
            content: Response content
            
        Returns:
            Send result dictionary
        """
        message = P2PMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.RESPONSE,
            in_reply_to=original_message_id
        )
        
        result = await self.connection_manager.send_message(
            from_username=self.agent_id,
            to_username=to_agent,
            content=content,
            urgency="MEDIUM"
        )
        
        if result.get("success"):
            self.message_history.append(message)
            logger.info(f"Response sent from {self.agent_id} to {to_agent}")
        
        return result
    
    async def send_urgent_message(
        self,
        to_agent: str,
        content: str
    ) -> dict[str, Any]:
        """
        Send an urgent message (requires checkpoint).
        
        Args:
            to_agent: Recipient agent ID
            content: Message content
            
        Returns:
            Send result dictionary
        """
        message = P2PMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.URGENT,
            urgency="CRITICAL",
            requires_response=True
        )
        
        result = await self.connection_manager.send_message(
            from_username=self.agent_id,
            to_username=to_agent,
            content=content,
            urgency="CRITICAL"
        )
        
        if result.get("success"):
            self.message_history.append(message)
            logger.info(f"URGENT message sent from {self.agent_id} to {to_agent}")
        
        return result
    
    async def send_notification(
        self,
        to_agent: str,
        content: str
    ) -> dict[str, Any]:
        """
        Send a notification (does not require response).
        
        Args:
            to_agent: Recipient agent ID
            content: Notification content
            
        Returns:
            Send result dictionary
        """
        message = P2PMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            message_type=MessageType.NOTIFICATION,
            urgency="LOW",
            requires_response=False
        )
        
        result = await self.connection_manager.send_message(
            from_username=self.agent_id,
            to_username=to_agent,
            content=content,
            urgency="LOW"
        )
        
        if result.get("success"):
            self.message_history.append(message)
            logger.info(f"Notification sent from {self.agent_id} to {to_agent}")
        
        return result
    
    async def process_incoming_message(
        self,
        message_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Process an incoming message.
        
        Args:
            message_data: Raw message data
            
        Returns:
            Action to take, if any
        """
        message = P2PMessage.from_dict(message_data)
        self.message_history.append(message)
        
        if message.message_type == MessageType.REQUEST and message.requires_response:
            return {
                "action": "send_response",
                "to": message.from_agent,
                "original_message_id": message.message_id,
                "content": f"Received your message: {message.content}"
            }
        
        if message.message_type == MessageType.URGENT:
            logger.warning(
                f"URGENT message received from {message.from_agent}: "
                f"{message.content}"
            )
            return {
                "action": "checkpoint_required",
                "from": message.from_agent,
                "message_id": message.message_id
            }
        
        return None
    
    def register_response_handler(self, message_id: str, handler: Callable) -> None:
        """Register a handler for a message response."""
        self.response_handlers[message_id] = handler
    
    def get_pending_requests(self) -> list[dict[str, Any]]:
        """Get pending requests."""
        return [msg.to_dict() for msg in self.pending_requests.values()]
    
    def get_message_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get message history."""
        return [msg.to_dict() for msg in self.message_history[-limit:]]
    
    def get_conversation_with(self, other_agent: str) -> list[dict[str, Any]]:
        """Get conversation with another agent."""
        return [
            msg.to_dict() for msg in self.message_history
            if msg.from_agent == other_agent or msg.to_agent == other_agent
        ]
    
    def get_stats(self) -> dict[str, Any]:
        """Get protocol statistics."""
        return {
            "agent_id": self.agent_id,
            "total_messages": len(self.message_history),
            "pending_requests": len(self.pending_requests),
            "response_handlers": len(self.response_handlers),
            "is_listening": self.is_listening
        }