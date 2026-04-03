"""Hook pattern matching — equivalente de matchesPattern() do Claude Code.

Suporta três tipos de patterns:
1. Exact match: "Write"
2. Pipe-separated OR: "Write|Edit|Read"
3. Regex pattern: "^Bash.*", ".*file.*"
"""

from __future__ import annotations

import logging
import re
from typing import Pattern

_logger = logging.getLogger(__name__)


class HookMatcher:
    """Matcher para padrões de hook (string, pipe-separated, regex).

    Inspirado em matchesPattern() do Claude Code (utils/hooks.ts:1336-1383).
    """

    @staticmethod
    def matches(query: str, pattern: str | None) -> bool:
        """Verifica se query corresponde ao pattern.

        Args:
            query: Nome da ferramenta (ex: "Write", "Bash", "read_file")
            pattern: Padrão de matching:
                - None ou "*" → match all
                - "Write" → exact match
                - "Write|Edit" → pipe-separated OR
                - "^Bash.*" → regex pattern

        Returns:
            True se query corresponde ao pattern

        Examples:
            >>> HookMatcher.matches("Write", None)
            True
            >>> HookMatcher.matches("Write", "Write")
            True
            >>> HookMatcher.matches("Write", "Write|Edit|Read")
            True
            >>> HookMatcher.matches("Bash", "^Bash.*")
            True
            >>> HookMatcher.matches("BashCommand", "^Bash.*")
            True
            >>> HookMatcher.matches("Write", "Edit")
            False
        """
        if not pattern or pattern == "*":
            return True

        # Check if it's a simple string or pipe-separated list (no regex special chars except |)
        if re.match(r"^[a-zA-Z0-9_|]+$", pattern):
            # Handle pipe-separated exact matches
            if "|" in pattern:
                patterns = [p.strip() for p in pattern.split("|")]
                return query in patterns

            # Simple exact match
            return query == pattern

        # Otherwise treat as regex
        try:
            regex = re.compile(pattern)
            return bool(regex.match(query))
        except re.error as exc:
            # If the regex is invalid, log error and return False
            _logger.error(
                "invalid_regex_pattern_in_hook_matcher",
                extra={"pattern": pattern, "error": str(exc)},
            )
            return False

    @staticmethod
    def compile_pattern(pattern: str) -> Pattern[str] | None:
        """Compila pattern para regex (cache optimization).

        Args:
            pattern: Pattern string to compile

        Returns:
            Compiled regex pattern, or None if invalid
        """
        try:
            return re.compile(pattern)
        except re.error as exc:
            _logger.error(
                "failed_to_compile_hook_pattern",
                extra={"pattern": pattern, "error": str(exc)},
            )
            return None

    @staticmethod
    def normalize_tool_name(tool_name: str) -> str:
        """Normaliza nome de ferramenta para matching.

        Converte snake_case para PascalCase para compatibilidade com
        padrões do Claude Code (ex: "read_file" → "ReadFile").

        Args:
            tool_name: Nome da ferramenta

        Returns:
            Nome normalizado
        """
        # Se já está em PascalCase, retorna como está
        if tool_name and tool_name[0].isupper():
            return tool_name

        # Converte snake_case para PascalCase
        parts = tool_name.split("_")
        return "".join(part.capitalize() for part in parts)
