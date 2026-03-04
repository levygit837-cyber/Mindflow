"""Logging interfaces.

Defines contracts for logging operations and agent log bus
for centralized log management.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from omnimind_backend.schemas.chat.agent import LogEntry, StreamEvent


@runtime_checkable
class Logger(Protocol):
    """Contract for logging implementations."""
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        ...

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        ...

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        ...

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        ...


@runtime_checkable
class AgentLogBus(Protocol):
    """Contract for agent log bus implementations."""
    
    async def publish(self, event: StreamEvent, turn_id: str) -> None:
        """Publish event to log bus."""
        ...

    async def get_recent(self, limit: int = 500) -> list[LogEntry]:
        """Get recent log entries."""
        ...

    async def clear_history(self) -> None:
        """Clear log history."""
        ...
