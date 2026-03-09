"""Backend infrastructure interfaces.

Defines contracts for backend execution, security,
and system operations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class BackendProtocol(Protocol):
    """Contract for backend execution implementations."""
    
    async def execute(self, command: str) -> Any:
        """Execute command securely in backend environment."""
        ...
    
    async def validate_permissions(self, user_id: str, operation: str) -> bool:
        """Validate user permissions for operation."""
        ...
    
    async def get_system_status(self) -> dict[str, Any]:
        """Get current system status."""
        ...
