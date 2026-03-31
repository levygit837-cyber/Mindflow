"""
Unit tests for Command Parser.
"""

import pytest
from mindflow_backend.commands.parser import CommandParser, ParsedCommand


@pytest.mark.unit
class TestCommandParser:
    """Test suite for CommandParser."""

    def test_parse_simple_command(self):
        """Test parsing a simple command without arguments."""
        parser = CommandParser()
        result = parser.parse("/help")

        assert result is not None
        assert result.command_name == "help"
        assert result.args == []
        assert result.raw_input == "/help"

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        parser = CommandParser()
        result = parser.parse("/agents spawn planner")

        assert result is not None
        assert result.command_name == "agents"
        assert result.args == ["spawn", "planner"]

    def test_parse_command_with_quoted_args(self):
        """Test parsing command with quoted arguments containing spaces."""
        parser = CommandParser()
        result = parser.parse('/memory search "user authentication flow"')

        assert result is not None
        assert result.command_name == "memory"
        assert result.args == ["search", "user authentication flow"]

    def test_parse_command_with_mixed_quotes(self):
        """Test parsing command with both single and double quotes."""
        parser = CommandParser()
        result = parser.parse("/config set key 'value with spaces'")

        assert result is not None
        assert result.command_name == "config"
        assert result.args == ["set", "key", "value with spaces"]

    def test_parse_non_command_returns_none(self):
        """Test that non-command text returns None."""
        parser = CommandParser()

        assert parser.parse("hello world") is None
        assert parser.parse("this is not a command") is None
        assert parser.parse("") is None

    def test_parse_command_with_leading_whitespace(self):
        """Test parsing command with leading whitespace."""
        parser = CommandParser()
        result = parser.parse("  /help  ")

        assert result is not None
        assert result.command_name == "help"

    def test_parse_command_with_trailing_whitespace(self):
        """Test parsing command with trailing whitespace."""
        parser = CommandParser()
        result = parser.parse("/status   ")

        assert result is not None
        assert result.command_name == "status"
        assert result.args == []

    def test_parse_command_with_empty_quotes(self):
        """Test parsing command with empty quoted strings."""
        parser = CommandParser()
        result = parser.parse('/test "" arg2')

        assert result is not None
        assert result.command_name == "test"
        assert result.args == ["", "arg2"]

    def test_parse_command_with_escaped_quotes(self):
        """Test parsing command with escaped quotes."""
        parser = CommandParser()
        result = parser.parse(r'/test "arg with \"nested\" quotes"')

        assert result is not None
        assert result.command_name == "test"
        assert result.args == ['arg with "nested" quotes']

    def test_is_command_true(self):
        """Test is_command returns True for commands."""
        parser = CommandParser()

        assert parser.is_command("/help") is True
        assert parser.is_command("  /status  ") is True
        assert parser.is_command("/agents spawn") is True

    def test_is_command_false(self):
        """Test is_command returns False for non-commands."""
        parser = CommandParser()

        assert parser.is_command("hello") is False
        assert parser.is_command("") is False
        assert parser.is_command("  ") is False
        assert parser.is_command("not a /command") is False

    def test_extract_command_name(self):
        """Test extracting command name from input."""
        parser = CommandParser()

        assert parser.extract_command_name("/help") == "help"
        assert parser.extract_command_name("/agents spawn") == "agents"
        assert parser.extract_command_name("  /status  ") == "status"

    def test_extract_command_name_non_command(self):
        """Test extracting command name from non-command returns None."""
        parser = CommandParser()

        assert parser.extract_command_name("hello") is None
        assert parser.extract_command_name("") is None


@pytest.mark.unit
class TestParsedCommand:
    """Test suite for ParsedCommand dataclass."""

    def test_parsed_command_creation(self):
        """Test creating ParsedCommand instance."""
        cmd = ParsedCommand(
            command_name="help",
            args=["topic"],
            raw_input="/help topic",
        )

        assert cmd.command_name == "help"
        assert cmd.args == ["topic"]
        assert cmd.raw_input == "/help topic"

    def test_parsed_command_immutable(self):
        """Test that ParsedCommand is immutable."""
        cmd = ParsedCommand(
            command_name="help",
            args=[],
            raw_input="/help",
        )

        with pytest.raises(AttributeError):
            cmd.command_name = "status"  # type: ignore
