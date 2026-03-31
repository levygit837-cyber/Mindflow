"""
Dynamic command loader for discovering commands from multiple sources.

Loads commands from:
- Built-in commands directory
- Custom commands directory
- Skills directory (future)
- Plugins (future)
"""

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any

from mindflow_backend.commands.registry import CommandRegistry, get_registry
from mindflow_backend.commands.types import Command, CommandMetadata

logger = logging.getLogger(__name__)


class CommandLoader:
    """
    Loads commands dynamically from multiple sources.

    Discovers and registers commands from:
    - Built-in commands (commands/builtin/)
    - Custom commands (commands/custom/)
    - Skills directory (future integration)
    - Plugins (future integration)
    """

    def __init__(self, registry: CommandRegistry | None = None):
        """
        Initialize command loader.

        Args:
            registry: Command registry (uses global if None)
        """
        self._registry = registry or get_registry()

    async def load_all_commands(self) -> int:
        """
        Load commands from all sources.

        Returns:
            Total number of commands loaded
        """
        total = 0

        # Load built-in commands
        builtin_count = await self.load_builtin_commands()
        total += builtin_count
        logger.info(f"Loaded {builtin_count} built-in commands")

        # Load custom commands
        custom_count = await self.load_custom_commands()
        total += custom_count
        logger.info(f"Loaded {custom_count} custom commands")

        # TODO: Load skill commands (Phase 3.2)
        # TODO: Load plugin commands (future)

        logger.info(f"Total commands loaded: {total}")
        return total

    async def load_builtin_commands(self, path: str | None = None) -> int:
        """
        Load built-in commands from directory.

        Args:
            path: Path to builtin commands directory (uses default if None)

        Returns:
            Number of commands loaded
        """
        if path is None:
            path = self._get_builtin_commands_path()

        return await self._load_commands_from_directory(path, source="builtin")

    async def load_custom_commands(self, path: str | None = None) -> int:
        """
        Load custom commands from directory.

        Args:
            path: Path to custom commands directory (uses default if None)

        Returns:
            Number of commands loaded
        """
        if path is None:
            path = self._get_custom_commands_path()

        return await self._load_commands_from_directory(path, source="custom")

    async def _load_commands_from_directory(
        self, directory: str, source: str = "unknown"
    ) -> int:
        """
        Load commands from a directory.

        Args:
            directory: Directory path to scan
            source: Source identifier for logging

        Returns:
            Number of commands loaded
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            logger.warning(f"Command directory does not exist: {directory}")
            return 0

        if not dir_path.is_dir():
            logger.warning(f"Path is not a directory: {directory}")
            return 0

        loaded_count = 0

        # Scan for Python files
        for py_file in dir_path.glob("*.py"):
            # Skip __init__.py and private files
            if py_file.name.startswith("_"):
                continue

            try:
                commands = await self._load_commands_from_file(py_file)
                for cmd in commands:
                    try:
                        self._registry.register(cmd)
                        loaded_count += 1
                        logger.debug(
                            f"Registered command '{cmd.metadata.name}' from {source}"
                        )
                    except ValueError as e:
                        logger.warning(
                            f"Failed to register command from {py_file.name}: {e}"
                        )
            except Exception as e:
                logger.error(
                    f"Error loading commands from {py_file.name}: {e}",
                    exc_info=True,
                )

        return loaded_count

    async def _load_commands_from_file(self, file_path: Path) -> list[Command]:
        """
        Load command classes from a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            List of command instances
        """
        commands: list[Command] = []

        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(
                f"mindflow_commands.{file_path.stem}", file_path
            )
            if spec is None or spec.loader is None:
                logger.warning(f"Could not load spec for {file_path}")
                return commands

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find command classes in module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if self._is_command_class(obj):
                    # Instantiate command
                    try:
                        command_instance = obj()
                        commands.append(command_instance)
                        logger.debug(f"Found command class: {name}")
                    except Exception as e:
                        logger.error(
                            f"Error instantiating command {name}: {e}",
                            exc_info=True,
                        )

        except Exception as e:
            logger.error(
                f"Error loading module from {file_path}: {e}",
                exc_info=True,
            )

        return commands

    def _is_command_class(self, obj: Any) -> bool:
        """
        Check if object is a valid command class.

        Args:
            obj: Object to check

        Returns:
            True if object is a valid command class
        """
        if not inspect.isclass(obj):
            return False

        # Check for required metadata attribute
        if not hasattr(obj, "metadata"):
            return False

        # Check metadata is CommandMetadata
        metadata = getattr(obj, "metadata", None)
        if not isinstance(metadata, CommandMetadata):
            return False

        # Check for execute method
        if not hasattr(obj, "execute"):
            return False

        # Check execute is callable
        execute = getattr(obj, "execute")
        if not callable(execute):
            return False

        return True

    def _get_builtin_commands_path(self) -> str:
        """Get path to built-in commands directory."""
        # Get path relative to this file
        current_file = Path(__file__)
        commands_dir = current_file.parent
        builtin_dir = commands_dir / "builtin"
        return str(builtin_dir)

    def _get_custom_commands_path(self) -> str:
        """Get path to custom commands directory."""
        # Get path relative to this file
        current_file = Path(__file__)
        commands_dir = current_file.parent
        custom_dir = commands_dir / "custom"
        return str(custom_dir)
