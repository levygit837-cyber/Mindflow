"""
Command parser for slash commands.

Parses user input to detect and extract slash commands with arguments.
Supports quoted arguments for strings containing spaces.
"""

import re
import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCommand:
    """Parsed command with name and arguments."""

    command_name: str
    args: list[str]
    raw_input: str


class CommandParser:
    """
    Parser for slash commands.

    Detects commands starting with '/' and extracts command name and arguments.
    Supports quoted arguments for strings containing spaces.

    Examples:
        /help
        /agents spawn planner
        /memory search "user authentication"
        /config set key 'value with spaces'
    """

    COMMAND_PATTERN = re.compile(r"^\s*/(\w+)")

    def is_command(self, text: str) -> bool:
        """
        Check if text is a command.

        Args:
            text: Input text to check

        Returns:
            True if text starts with '/', False otherwise
        """
        if not text or not text.strip():
            return False

        return bool(self.COMMAND_PATTERN.match(text))

    def extract_command_name(self, text: str) -> str | None:
        """
        Extract command name from text.

        Args:
            text: Input text

        Returns:
            Command name without '/' prefix, or None if not a command
        """
        match = self.COMMAND_PATTERN.match(text)
        if match:
            return match.group(1)
        return None

    def parse(self, text: str) -> ParsedCommand | None:
        """
        Parse command from text.

        Args:
            text: Input text to parse

        Returns:
            ParsedCommand if text is a valid command, None otherwise

        Examples:
            >>> parser = CommandParser()
            >>> parser.parse("/help")
            ParsedCommand(command_name='help', args=[], raw_input='/help')

            >>> parser.parse("/agents spawn planner")
            ParsedCommand(command_name='agents', args=['spawn', 'planner'], ...)

            >>> parser.parse('/memory search "user auth"')
            ParsedCommand(command_name='memory', args=['search', 'user auth'], ...)
        """
        if not self.is_command(text):
            return None

        # Extract command name
        command_name = self.extract_command_name(text)
        if not command_name:
            return None

        # Extract arguments after command name
        # Remove leading slash and command name
        match = self.COMMAND_PATTERN.match(text)
        if not match:
            return None

        args_text = text[match.end() :].strip()

        # Parse arguments using shlex to handle quoted strings
        args: list[str] = []
        if args_text:
            try:
                args = shlex.split(args_text)
            except ValueError:
                # If shlex fails (e.g., unclosed quotes), fall back to simple split
                args = args_text.split()

        return ParsedCommand(
            command_name=command_name,
            args=args,
            raw_input=text,
        )
