"""
Team Chat for MindFlow agent groups.

Adapted from Plexo project for MindFlow architecture.
Uses MUC (Multi-User Chat) for team communication.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TeamMessage:
    """Message sent in team chat."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str = ""
    sender_jid: str = ""
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    reference_message_id: str | None = None
    message_type: str = "chat"
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "team_id": self.team_id,
            "sender_jid": self.sender_jid,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "reference_message_id": self.reference_message_id,
            "message_type": self.message_type,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TeamMessage':
        """Create instance from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            team_id=data.get("team_id", ""),
            sender_jid=data.get("sender_jid", ""),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            reference_message_id=data.get("reference_message_id"),
            message_type=data.get("message_type", "chat"),
            metadata=data.get("metadata", {})
        )


class TeamChat:
    """
    Team chat using MUC (Multi-User Chat).
    
    Manages chat history and message operations for team communication.
    """
    
    def __init__(self, team_id: str, room_jid: str):
        self.team_id = team_id
        self.room_jid = room_jid
        self.message_history: list[TeamMessage] = []
        self.max_history_size: int = 1000
    
    def create_message(
        self,
        sender_jid: str,
        content: str,
        reference_message_id: str | None = None,
        message_type: str = "chat",
        metadata: dict[str, Any] | None = None
    ) -> TeamMessage:
        """
        Create a message for the team.
        
        Args:
            sender_jid: Sender JID
            content: Message content
            reference_message_id: Optional reference to another message
            message_type: Message type
            metadata: Optional metadata
            
        Returns:
            Created TeamMessage
        """
        message = TeamMessage(
            team_id=self.team_id,
            sender_jid=sender_jid,
            content=content,
            reference_message_id=reference_message_id,
            message_type=message_type,
            metadata=metadata or {}
        )
        
        self.message_history.append(message)
        
        # Trim history if too large
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]
        
        return message
    
    def get_recent_messages(self, limit: int = 50) -> list[TeamMessage]:
        """Get recent messages."""
        return self.message_history[-limit:]
    
    def get_message(self, message_id: str) -> TeamMessage | None:
        """Get message by ID."""
        for msg in self.message_history:
            if msg.message_id == message_id:
                return msg
        return None
    
    def get_messages_by_sender(self, sender_jid: str) -> list[TeamMessage]:
        """Get messages by sender."""
        return [m for m in self.message_history if m.sender_jid == sender_jid]
    
    def get_messages_referencing(self, message_id: str) -> list[TeamMessage]:
        """Get messages that reference a specific message."""
        return [
            m for m in self.message_history
            if m.reference_message_id == message_id
        ]
    
    def search_messages(self, query: str) -> list[TeamMessage]:
        """Search messages by content."""
        query_lower = query.lower()
        return [
            m for m in self.message_history
            if query_lower in m.content.lower()
        ]
    
    def clear_history(self) -> int:
        """Clear message history."""
        count = len(self.message_history)
        self.message_history = []
        return count
    
    def get_stats(self) -> dict[str, Any]:
        """Get chat statistics."""
        senders = set(m.sender_jid for m in self.message_history)
        referenced_messages = set(
            m.reference_message_id
            for m in self.message_history
            if m.reference_message_id
        )
        
        return {
            "team_id": self.team_id,
            "room_jid": self.room_jid,
            "total_messages": len(self.message_history),
            "unique_senders": len(senders),
            "referenced_messages": len(referenced_messages),
            "history_size": len(self.message_history)
        }