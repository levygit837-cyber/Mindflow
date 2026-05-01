"""File context provider for QueryEngine."""

from __future__ import annotations

import re
from pathlib import Path

from mindflow_backend.query.providers.base import BaseContextProvider


class FileProvider(BaseContextProvider):
    """Fetch small explicitly mentioned files from the current workspace."""

    priority = 60

    def __init__(self, root_path: str | None = None) -> None:
        self.root_path = Path(root_path or Path.cwd()).resolve()

    @property
    def name(self) -> str:
        return "file"

    async def fetch(self, query: str, max_tokens: int = 0) -> str | None:
        del max_tokens

        file_pattern = r"\b[\w\-_/\.]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md|txt|sql)\b"
        matches = sorted(set(re.findall(file_pattern, query or "", re.IGNORECASE)))
        if not matches:
            return None

        sections: list[str] = []
        for match in matches[:5]:
            candidate = (self.root_path / match).resolve()
            if not str(candidate).startswith(str(self.root_path)):
                continue
            if not candidate.is_file():
                continue
            try:
                content = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            sections.append(f"## {match}\n\n{content[:4000]}")

        return "\n\n".join(sections) if sections else None
