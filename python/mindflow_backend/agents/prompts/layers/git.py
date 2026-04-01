"""Git context layer — injects git status into system prompt.

Uses existing GitProvider to fetch git info.
"""

from __future__ import annotations

import logging

from mindflow_backend.agents.prompts.assembler import AssemblyContext

logger = logging.getLogger(__name__)


class GitContextLayer:
    """Injeta status do git no system prompt."""

    name = "git"
    priority = 70  # Prioridade média-alta

    async def render(self, context: AssemblyContext) -> str | None:
        working_dir = context.working_directory
        if not working_dir:
            return None

        try:
            from mindflow_backend.query.providers.git_provider import GitProvider

            provider = GitProvider()
            git_info = await provider.fetch("", max_tokens=500)
            if not git_info:
                return None
            return f"## Git Status\n\n{git_info}"
        except Exception:
            logger.debug("Failed to fetch git context", exc_info=True)
            return None