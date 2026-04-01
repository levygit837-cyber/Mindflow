"""Bash AST Parser — AST-based command parsing for security analysis.

Uses bashlex (if available) to parse bash commands into an AST,
enabling accurate detection of dangerous patterns that string-based
matching would miss (e.g., command substitution, nested quoting).

Adapted from Claude Code's splitCommand_DEPRECATED() approach.

Fallback: If bashlex is not installed, falls back to regex-based splitting.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Iterator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AST Node representation
# ---------------------------------------------------------------------------


@dataclass
class BashASTNode:
    """Represents a parsed bash command node."""

    kind: str  # "command", "pipeline", "list", "compound", "assignment", "reserved"
    value: str  # Original string
    word: str | None = None  # First word (command name)
    parts: list[BashASTNode] = field(default_factory=list)  # Child nodes
    redirects: list[dict[str, Any]] = field(default_factory=list)
    assignments: list[dict[str, str]] = field(default_factory=list)
    line: int = 0
    column: int = 0
    is_dangerous: bool = False
    danger_reason: str | None = None


# ---------------------------------------------------------------------------
# Parser class
# ---------------------------------------------------------------------------


class BashCommandParser:
    """Parse bash commands into AST for security analysis.
    
    Attempts to use bashlex for proper AST parsing. Falls back to
    regex-based splitting if bashlex is unavailable.
    """

    bashlex_available: bool = False

    def __init__(self) -> None:
        self._try_import_bashlex()

    def _try_import_bashlex(self) -> None:
        """Try to import bashlex, set availability flag."""
        try:
            import bashlex  # noqa: F401

            BashCommandParser.bashlex_available = True
        except ImportError:
            BashCommandParser.bashlex_available = False
            logger.warning(
                "bashlex not available — falling back to regex-based command parsing. "
                "Install with: pip install bashlex"
            )

    def parse(self, command: str) -> list[BashASTNode]:
        """Parse a command string into a list of AST nodes.
        
        Handles compound commands (&&, ||, ;, |, newlines) by splitting
        into individual nodes.
        
        Args:
            command: The bash command string to parse.
            
        Returns:
            List of BashASTNode objects representing parsed commands.
        """
        if not command or not command.strip():
            return []

        if BashCommandParser.bashlex_available:
            return self._parse_with_bashlex(command)
        return self._parse_with_regex(command)

    def _parse_with_bashlex(self, command: str) -> list[BashASTNode]:
        """Parse using bashlex library for accurate AST."""
        import bashlex

        nodes: list[BashASTNode] = []

        try:
            parsed_commands = bashlex.parse(command)

            for cmd in parsed_commands:
                node = self._convert_bashlex_node(cmd, command)
                nodes.append(node)

        except Exception as e:
            logger.warning(
                "bashlex parsing failed for '%s': %s — falling back to regex",
                command[:100],
                e,
            )
            return self._parse_with_regex(command)

        return nodes

    def _convert_bashlex_node(
        self, node: Any, source: str, depth: int = 0
    ) -> BashASTNode:
        """Convert a bashlex node to our BashASTNode."""
        kind = node.kind

        # Extract position info
        pos = node.pos if hasattr(node, "pos") else (0, 0)
        line = node.line if hasattr(node, "line") else 0
        column = node.column if hasattr(node, "column") else 0

        # Prevent deep recursion
        if depth > 10:
            return BashASTNode(
                kind=f"{kind}_deep",
                value=source[pos[0] : pos[1]] if pos else source,
                word=None,
                line=line,
                column=column,
                is_dangerous=True,
                danger_reason="nesting depth exceeded",
            )

        # Extract first word (command name) for simple commands
        word = None
        if kind == "command" and hasattr(node, "parts") and node.parts:
            first_part = node.parts[0]
            if hasattr(first_part, "word"):
                word = first_part.word

        # Check for dangerous patterns
        is_dangerous, danger_reason = self._check_node_danger(node, kind)

        # Recursively convert child parts
        parts: list[BashASTNode] = []
        if hasattr(node, "parts"):
            for part in node.parts:
                parts.append(self._convert_bashlex_node(part, source, depth + 1))

        # Extract assignments
        assignments: list[dict[str, str]] = []
        if hasattr(node, "assignments"):
            for assign in node.assignments:
                assignments.append(
                    {
                        "name": getattr(assign, "word", str(assign)),
                        "value": getattr(assign, "value", ""),
                    }
                )

        # Extract redirects
        redirects: list[dict[str, Any]] = []
        if hasattr(node, "redirects"):
            for redir in node.redirects:
                redirects.append(
                    {
                        "type": getattr(redir, "type", "unknown"),
                        "target": str(getattr(redir, "n", "")),
                    }
                )

        return BashASTNode(
            kind=kind,
            value=source[pos[0] : pos[1]] if pos else source,
            word=word,
            parts=parts,
            redirects=redirects,
            assignments=assignments,
            line=line,
            column=column,
            is_dangerous=is_dangerous,
            danger_reason=danger_reason,
        )

    def _check_node_danger(self, node: Any, kind: str) -> tuple[bool, str | None]:
        """Check if a bashlex node indicates a dangerous pattern."""
        if kind == "command":
            if not hasattr(node, "parts") or not node.parts:
                return False, None

            first_word = ""
            if hasattr(node.parts[0], "word"):
                first_word = node.parts[0].word
            elif hasattr(node.parts[0], "value"):
                first_word = node.parts[0].value

            dangerous_commands = {
                "eval",
                "exec",
                "source",
                "bash",
                "sh",
                "zsh",
                "curl",
                "wget",
                "nc",
                "ncat",
                "socat",
                "python",
                "python3",
                "perl",
                "ruby",
                "node",
                "lua",
                "php",
            }

            if first_word.lower() in dangerous_commands:
                return True, f"dangerous command: {first_word}"

        elif kind == "commandsubstitution":
            return True, "command substitution $(...)"

        elif kind == "processsubstitution":
            return True, "process substitution <(...)"

        elif kind == "here" and hasattr(node, "body"):
            if getattr(node.body, "kind", None) == "list":
                return True, "complex here document"

        return False, None

    def _parse_with_regex(self, command: str) -> list[BashASTNode]:
        """Fallback regex-based command parsing."""
        nodes: list[BashASTNode] = []

        # Split compound commands: &&, ||, ;, newlines
        # This is a simplified split — bashlex handles quoting/escaping better
        subcommands = self._split_compound_command(command)

        for subcmd in subcommands:
            subcmd = subcmd.strip()
            if not subcmd:
                continue

            parts = subcmd.split()
            word = parts[0] if parts else None

            # Check for dangerous patterns
            is_dangerous, danger_reason = self._check_regex_danger(subcmd)

            nodes.append(
                BashASTNode(
                    kind="command",
                    value=subcmd,
                    word=word,
                    is_dangerous=is_dangerous,
                    danger_reason=danger_reason,
                )
            )

        return nodes

    def _split_compound_command(self, command: str) -> list[str]:
        """Split compound command by &&, ||, ;, and newlines.
        
        Handles basic quoting but not all edge cases. For accurate parsing,
        use bashlex.
        """
        subcommands: list[str] = []
        current: list[str] = []
        in_single_quote = False
        in_double_quote = False
        i = 0

        while i < len(command):
            char = command[i]

            # Handle escape sequences
            if char == "\\":
                current.append(char)
                if i + 1 < len(command):
                    current.append(command[i + 1])
                    i += 2
                continue

            # Handle quotes
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                # Check for compound command separators
                if char == ";" or char == "&" or char == "|":
                    # Handle &&, ||, |, and pipes
                    if i + 1 < len(command):
                        next_char = command[i + 1]
                        if char == "&" and next_char == "&":
                            subcommands.append("".join(current).strip())
                            current = []
                            i += 2
                            continue
                        elif char == "|" and next_char == "|":
                            subcommands.append("".join(current).strip())
                            current = []
                            i += 2
                            continue
                        elif char == "|" and next_char != "|":
                            # Pipe — keep parts together for security analysis
                            pass

            current.append(char)
            i += 1

        # Add remaining
        remaining = "".join(current).strip()
        if remaining:
            subcommands.append(remaining)

        return subcommands

    def _check_regex_danger(self, command: str) -> tuple[bool, str | None]:
        """Check for dangerous patterns using regex."""
        # Command substitution
        if "$(" in command or "`" in command:
            return True, "command substitution detected"

        # Dangerous commands at start
        dangerous_pattern = re.compile(
            r"^\s*(eval|exec|source)\s", re.IGNORECASE
        )
        if dangerous_pattern.match(command):
            return True, "dangerous command: eval/exec/source"

        # Environment variable assignment before command
        if re.match(r"^[A-Z_]+\s*=", command):
            # Check for dangerous env vars
            hijack_vars = [
                "LD_PRELOAD",
                "LD_LIBRARY_PATH",
                "LD_AUDIT",
                "PYTHONPATH",
                "PYTHONINSPECT",
                "BASH_ENV",
            ]
            for var in hijack_vars:
                if command.startswith(f"{var}="):
                    return True, f"binary hijack via {var}"

        return False, None

    def get_subcommands(self, command: str) -> list[str]:
        """Extract individual subcommands from a compound command.
        
        Example:
            "echo safe && rm -rf /" -> ["echo safe", "rm -rf /"]
        """
        nodes = self.parse(command)
        return [node.value for node in nodes if node.value.strip()]

    def get_command_names(self, command: str) -> list[str]:
        """Extract all command names from a (possibly compound) command.
        
        Example:
            "git status && npm test" -> ["git", "npm"]
        """
        nodes = self.parse(command)
        names: list[str] = []
        for node in nodes:
            if node.word:
                # Handle full paths: /usr/bin/git -> git
                import os.path
                names.append(os.path.basename(node.word))
            for part in node.parts:
                if part.word:
                    import os.path
                    names.append(os.path.basename(part.word))
        return names

    def has_command_substitution(self, command: str) -> bool:
        """Check if command contains $(...) or backtick substitution."""
        nodes = self.parse(command)
        for node in nodes:
            if node.is_dangerous and node.danger_reason == "command substitution $(...)":
                return True
            for part in node.parts:
                if part.kind in ("commandsubstitution", "processsubstitution"):
                    return True
        # Fallback regex check
        return "$(" in command or "`" in command

    def get_env_assignments(self, command: str) -> dict[str, str]:
        """Extract environment variable assignments from command prefix.
        
        Example:
            "LD_PRELOAD=/tmp/evil.so ./target" -> {"LD_PRELOAD": "/tmp/evil.so"}
        """
        nodes = self.parse(command)
        assignments: dict[str, str] = {}
        for node in nodes:
            for assign in node.assignments:
                if "name" in assign and "value" in assign:
                    assignments[assign["name"]] = assign["value"]
        return assignments