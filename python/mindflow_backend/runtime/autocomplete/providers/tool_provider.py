"""Tool Provider for Autocomplete.

Sugere nomes de ferramentas disponíveis com match por similaridade.
"""

from __future__ import annotations

from mindflow_backend.runtime.autocomplete.engine import (
    AutocompleteRequest,
    Suggestion,
    SuggestionCategory,
)
from mindflow_backend.runtime.autocomplete.matchers.fuzzy_matcher import fuzzy_match
from mindflow_backend.runtime.autocomplete.matchers.prefix_matcher import prefix_match


class ToolProvider:
    """Provider de ferramentas.

    Sugere nomes de ferramentas disponíveis no sistema.
    Match por similaridade com inclusão de descrição.

    Usage:
        provider = ToolProvider()
        suggestions = await provider.get_suggestions(
            AutocompleteRequest(input_text="read")
        )
    """

    # Ferramentas disponíveis com descrições
    TOOLS: dict[str, str] = {
        "read_file": "Read contents of a file",
        "write_to_file": "Write content to a file",
        "replace_in_file": "Replace content in an existing file",
        "execute_command": "Execute a CLI command on the system",
        "search_files": "Search for patterns across files in a directory",
        "list_files": "List files and directories in a path",
        "ask_followup_question": "Ask the user a follow-up question",
        "attempt_completion": "Present the result of completed work",
        "browser_action": "Interact with a browser",
        "use_mcp_tool": "Use a tool provided by an MCP server",
        "codebase_search": "Search codebase semantically",
        "codebase_index": "Start indexing a codebase",
        "codebase_status": "Check index status",
    }

    async def get_suggestions(
        self, request: AutocompleteRequest
    ) -> list[Suggestion]:
        """Retorna sugestões de ferramentas baseadas no input."""
        input_text = request.input_text.strip().lower()

        if not input_text:
            return []

        suggestions: list[Suggestion] = []

        for tool_name, description in self.TOOLS.items():
            # Calcular score combinando prefix e fuzzy
            prefix_score = prefix_match(input_text, tool_name.lower())
            fuzzy_score = fuzzy_match(input_text, tool_name.lower())

            # Usar o melhor score
            score = max(prefix_score, fuzzy_score)

            if score > 0.2:
                suggestions.append(
                    Suggestion(
                        text=tool_name,
                        display_text=tool_name,
                        description=description,
                        category=SuggestionCategory.TOOL,
                        score=score,
                    )
                )

        return suggestions