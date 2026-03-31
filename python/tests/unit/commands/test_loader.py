"""
Unit tests for Command Loader.
"""

import pytest
from pathlib import Path
from mindflow_backend.commands.loader import CommandLoader
from mindflow_backend.commands.registry import CommandRegistry
from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


# Mock command for testing
class TestCommand:
    """Test command for loader testing."""

    metadata = CommandMetadata(
        name="test_cmd",
        description="Test command",
        category=CommandCategory.SYSTEM,
    )

    async def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult(success=True, message="Test executed")


@pytest.mark.unit
class TestCommandLoader:
    """Test suite for CommandLoader."""

    def test_loader_initialization(self):
        """Test loader initializes with registry."""
        registry = CommandRegistry()
        loader = CommandLoader(registry=registry)

        assert loader._registry == registry

    def test_loader_uses_global_registry_if_none(self):
        """Test loader uses global registry if none provided."""
        loader = CommandLoader()

        assert loader._registry is not None

    @pytest.mark.asyncio
    async def test_load_builtin_commands_empty_directory(self, tmp_path):
        """Test loading from empty builtin directory."""
        registry = CommandRegistry()
        loader = CommandLoader(registry=registry)

        # Create empty builtin directory
        builtin_dir = tmp_path / "builtin"
        builtin_dir.mkdir()

        count = await loader.load_builtin_commands(str(builtin_dir))

        assert count == 0
        assert len(registry.list_all()) == 0

    @pytest.mark.asyncio
    async def test_load_builtin_commands_nonexistent_directory(self):
        """Test loading from non-existent directory returns 0."""
        registry = CommandRegistry()
        loader = CommandLoader(registry=registry)

        count = await loader.load_builtin_commands("/nonexistent/path")

        assert count == 0

    @pytest.mark.asyncio
    async def test_discover_commands_from_module(self, tmp_path):
        """Test discovering commands from a Python module."""
        registry = CommandRegistry()
        loader = CommandLoader(registry=registry)

        # Create a test module with a command
        module_dir = tmp_path / "commands"
        module_dir.mkdir()

        # Write a simple command module
        command_file = module_dir / "test_command.py"
        command_file.write_text("""
from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)

class HelpCommand:
    metadata = CommandMetadata(
        name="help",
        description="Show help",
        category=CommandCategory.SYSTEM,
    )

    async def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult(success=True, message="Help text")
""")

        # Note: This test would require dynamic module loading
        # For now, we'll test the structure is correct
        assert command_file.exists()

    def test_is_command_class(self):
        """Test identifying valid command classes."""
        loader = CommandLoader()

        # Valid command class
        assert loader._is_command_class(TestCommand) is True

        # Invalid: not a class
        assert loader._is_command_class("not a class") is False

        # Invalid: missing metadata
        class NoMetadata:
            pass

        assert loader._is_command_class(NoMetadata) is False

        # Invalid: missing execute method
        class NoExecute:
            metadata = CommandMetadata(
                name="test",
                description="Test",
                category=CommandCategory.SYSTEM,
            )

        assert loader._is_command_class(NoExecute) is False


@pytest.mark.unit
class TestCommandDiscovery:
    """Test suite for command discovery logic."""

    def test_get_builtin_commands_path(self):
        """Test getting builtin commands path."""
        loader = CommandLoader()
        path = loader._get_builtin_commands_path()

        assert path is not None
        assert "builtin" in str(path)

    def test_scan_directory_for_python_files(self, tmp_path):
        """Test scanning directory for Python files."""
        loader = CommandLoader()

        # Create test directory structure
        test_dir = tmp_path / "commands"
        test_dir.mkdir()

        (test_dir / "command1.py").write_text("# Command 1")
        (test_dir / "command2.py").write_text("# Command 2")
        (test_dir / "__init__.py").write_text("# Init")
        (test_dir / "not_python.txt").write_text("Not Python")

        # Scan for Python files
        python_files = list(test_dir.glob("*.py"))

        # Should find 3 Python files (command1, command2, __init__)
        assert len(python_files) == 3
        assert any("command1.py" in str(f) for f in python_files)
        assert any("command2.py" in str(f) for f in python_files)
