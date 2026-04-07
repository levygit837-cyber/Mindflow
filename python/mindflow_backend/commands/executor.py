"""
Command executor with error handling and permission checks.

Executes commands with proper context and handles errors gracefully.
"""

import logging
from typing import Any

from mindflow_backend.commands.registry import CommandRegistry, get_registry
from mindflow_backend.commands.types import Command, CommandContext, CommandResult

logger = logging.getLogger(__name__)


class CommandExecutor:
    """
    Executes commands with context and error handling.

    Provides command execution with:
    - Permission checking (if permission system available)
    - Error handling with user-friendly messages
    - Result formatting
    - Async execution support
    """

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        permission_manager: Any | None = None,
    ):
        """
        Initialize command executor.

        Args:
            registry: Command registry (uses global if None)
            permission_manager: Permission manager for permission checks (optional)
        """
        self._registry = registry or get_registry()
        self._permission_manager = permission_manager

    async def execute(
        self,
        command_name: str,
        args: list[str],
        session_id: str,
        user_id: str | None = None,
        execution_id: str | None = None,
        raw_input: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommandResult:
        """
        Execute a command with given context.

        Args:
            command_name: Name of command to execute
            args: Command arguments
            session_id: Session ID for context
            user_id: User ID (optional)
            execution_id: Execution ID (optional)
            raw_input: Original raw input text (optional)
            metadata: Additional metadata (optional)

        Returns:
            CommandResult with success status and message

        Raises:
            No exceptions - all errors are caught and returned as CommandResult
        """
        try:
            # Get command from registry
            command = self._registry.get(command_name)
            if command is None:
                return CommandResult(
                    success=False,
                    message=f"Command '{command_name}' not found",
                    error="COMMAND_NOT_FOUND",
                )

            # Check permissions if permission manager available
            if self._permission_manager and command.metadata.permission_required:
                permission_result = await self._check_permission(
                    command=command,
                    session_id=session_id,
                    user_id=user_id,
                )
                if not permission_result:
                    return CommandResult(
                        success=False,
                        message=f"Permission denied for command '{command_name}'",
                        error="PERMISSION_DENIED",
                    )

            # Build command context
            context = CommandContext(
                session_id=session_id,
                user_id=user_id,
                execution_id=execution_id or self._generate_execution_id(),
                args=args,
                raw_input=raw_input or f"/{command_name} {' '.join(args)}",
                metadata=metadata or {},
            )

            # Execute command
            logger.info(
                f"Executing command '{command_name}' with args {args}",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "execution_id": context.execution_id,
                },
            )

            result = await command.execute(context)

            logger.info(
                f"Command '{command_name}' executed successfully: {result.success}",
                extra={
                    "session_id": session_id,
                    "execution_id": context.execution_id,
                    "success": result.success,
                },
            )

            return result

        except Exception as e:
            logger.exception(
                f"Error executing command '{command_name}'",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            )

            return CommandResult(
                success=False,
                message=f"Error executing command: {str(e)}",
                error="EXECUTION_ERROR",
                data={"exception_type": type(e).__name__},
            )

    async def _check_permission(
        self,
        command: Command,
        session_id: str,
        user_id: str | None,
    ) -> bool:
        """
        Check if user has permission to execute command.

        Args:
            command: Command to check permission for
            session_id: Session ID
            user_id: User ID

        Returns:
            True if permission granted, False otherwise
        """
        if self._permission_manager is None:
            return True

        try:
            # Integrate with PermissionManager
            from mindflow_backend.permissions.manager import PermissionManager
            from mindflow_backend.permissions.types import PermissionContext, PermissionMode
            
            # Build permission context
            perm_context = PermissionContext(
                session_id=session_id,
                user_id=user_id,
                mode=PermissionMode.DEFAULT,  # Could be configurable per command
            )
            
            # Check permission using the real permission system
            perm_manager = PermissionManager()
            result = await perm_manager.check_permission(
                tool_name=command.metadata.name,
                input={"args": getattr(context, "args", []), "kwargs": getattr(context, "kwargs", {})},
                context=perm_context,
            )
            
            # Handle permission result
            if result.behavior.value == "deny":
                logger.warning(
                    f"Command '{command.metadata.name}' denied by permission system",
                    extra={"session_id": session_id, "reason": result.reason},
                )
                return False
            elif result.behavior.value == "ask":
                # In command context, "ask" means we need explicit approval
                # For now, log and allow (could prompt user in interactive mode)
                logger.info(
                    f"Command '{command.metadata.name}' requires approval",
                    extra={"session_id": session_id, "message": result.message},
                )
                # Return True but could implement interactive prompting
                return True
            else:
                # Allowed
                return True
                
        except Exception as e:
            logger.error(
                f"Error checking permission for command '{command.metadata.name}'",
                extra={"error": str(e)},
            )
            # Fail closed - deny on error
            return False

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        import uuid

        return str(uuid.uuid4())
