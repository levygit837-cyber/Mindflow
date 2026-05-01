"""Backward-compatible database model aliases."""

from mindflow_backend.db.models import ChatMessage, ChatSession, Message, Session

__all__ = ["ChatMessage", "ChatSession", "Message", "Session"]
