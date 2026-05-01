"""Git context provider for QueryEngine."""

from __future__ import annotations

import asyncio
from pathlib import Path

from mindflow_backend.query.providers.base import BaseContextProvider


class GitProvider(BaseContextProvider):
    """Fetch lightweight Git status for prompt/context assembly."""

    priority = 80

    def __init__(self, root_path: str | None = None) -> None:
        self.root_path = Path(root_path or Path.cwd())

    @property
    def name(self) -> str:
        return "git"

    async def _git(self, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=self.root_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace").strip()
            return error
        return stdout.decode("utf-8", errors="replace").strip()

    async def fetch(self, query: str, max_tokens: int = 0) -> str | None:
        del query, max_tokens

        branch = await self._git("branch", "--show-current")
        status = await self._git("status", "--short")
        diff_stat = await self._git("diff", "--stat")

        parts = []
        if branch:
            parts.append(f"Branch: {branch}")
        parts.append("Status:\n" + (status or "clean"))
        if diff_stat:
            parts.append("Diff stat:\n" + diff_stat)
        return "\n\n".join(parts).strip() or None
