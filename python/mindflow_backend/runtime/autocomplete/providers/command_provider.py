"""Command Provider for Autocomplete.

Sugere comandos slash (/help, /config, etc.) com match por prefixo.
"""

from __future__ import annotations

from mindflow_backend.runtime.autocomplete.engine import (
    AutocompleteRequest,
    Suggestion,
    SuggestionCategory,
)
from mindflow_backend.runtime.autocomplete.matchers.prefix_matcher import prefix_match


class CommandProvider:
    """Provider de comandos slash.

    Sugere comandos como /help, /config, /clear, etc.
    Match por prefixo com score mais alto para match exato.

    Usage:
        provider = CommandProvider()
        suggestions = await provider.get_suggestions(
            AutocompleteRequest(input_text="/hel")
        )
    """

    # Comandos disponíveis com suas descrições
    COMMANDS: dict[str, str] = {
        "/help": "Show help information",
        "/config": "Open configuration",
        "/clear": "Clear current session",
        "/reset": "Reset conversation context",
        "/status": "Show system status",
        "/model": "Switch AI model",
        "/tools": "List available tools",
        "/history": "Show command history",
        "/export": "Export conversation",
        "/debug": "Toggle debug mode",
        "/theme": "Change UI theme",
        "/version": "Show version info",
        "/feedback": "Send feedback",
        "/quit": "Exit the application",
    }

    async def get_suggestions(
        self, request: AutocompleteRequest
    ) -> list[Suggestion]:
        """Retorna sugestões de comandos baseadas no input."""
        input_text = request.input_text.strip()

        # Só sugere se input começa com /
        if not input_text.startswith("/"):
            return []

        suggestions: list[Suggestion] = []

        for cmd, description in self.COMMANDS.items():
            score = prefix_match(input_text, cmd)
            if score > 0:
                suggestions.append(
                    Suggestion(
                        text=cmd,
                        display_text=cmd,
                        description=description,
                        category=SuggestionCategory.COMMAND,
                        score=score,
                    )
                )

        return suggestions