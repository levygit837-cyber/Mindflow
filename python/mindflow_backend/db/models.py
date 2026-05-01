"""Compatibility aliases for legacy ``mindflow_backend.db.models`` imports."""

from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession

Session = ChatSession
Message = ChatMessage

__all__ = ["ChatSession", "ChatMessage", "Session", "Message"]
