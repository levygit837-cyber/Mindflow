"""
Base interface for MindFlow tools. Provides abstract interfaces and base classes
for implementing consistent tool behavior across the system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class ToolInterface(ABC):
    """
    Abstract base class for all MindFlow tools.
    """

    def __init__(self):
        self.name = ""
        self.description = ""
        self.version = "1.0.0"
        self.backend = None
        # Optional working directory propagated from the agent sandbox (root_dir feature).
        # Filesystem tools use this as base path when a relative path is supplied.
        self.root_dir: str | None = None
        # Optional chat session propagated by the runtime for session-scoped tools.
        self.session_id: str | None = None
        # Optional durable execution identifier propagated by the runtime.
        self.execution_id: str | None = None
        # Optional sandbox policy propagated by the registry/runtime.
        self.sandbox_mode = None
        self.secure_mode: bool = False

    @abstractmethod
    def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute the tool with given parameters.
        Args:
            **kwargs: Tool parameters
        Returns:
            Dictionary with execution result
        """
        pass

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """
        Get the tool schema definition.
        Returns:
            Dictionary containing tool schema
        """
        pass

    def _format_result(self, success: bool, result: Any | None = None, error: str | None = None) -> dict[str, Any]:
        """
        Format tool execution result consistently.
        Args:
            success: Whether execution was successful
            result: Result data (if successful)
            error: Error message (if failed)
        Returns:
            Formatted result dictionary
        """
        return {
            "success": success,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "tool": self.name,
            "version": self.version
        }


class AsyncToolInterface(ToolInterface):
    """
    Abstract base class for async MindFlow tools.
    """

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute the tool asynchronously with given parameters.
        Args:
            **kwargs: Tool parameters
        Returns:
            Dictionary with execution result
        """
        pass


class ToolResult:
    """
    Standard result format for tool executions.
    """

    def __init__(
        self,
        success: bool,
        data: Any | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary format.
        Returns:
            Dictionary representation
        """
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
