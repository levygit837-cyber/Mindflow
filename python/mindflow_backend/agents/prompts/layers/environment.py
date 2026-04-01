"""Environment context layer — injects OS, shell, datetime, CWD.

Equivalent to Claude Code's getUserContext() in context.ts.
Returns: datetime, OS, shell, CWD, timezone.
"""

from __future__ import annotations

import os
import platform
from datetime import datetime, timezone

from mindflow_backend.agents.prompts.assembler import AssemblyContext


class EnvironmentLayer:
    """Injeta contexto do ambiente no system prompt."""

    name = "environment"
    priority = 80  # Alta prioridade

    async def render(self, context: AssemblyContext) -> str:
        now = datetime.now(timezone.utc)
        working_dir = context.working_directory or os.getcwd()
        shell = os.environ.get("SHELL", "unknown")

        return (
            f"## Environment Details\n\n"
            f"Current Date: {now.strftime('%Y-%m-%d')}\n"
            f"Current Time: {now.strftime('%H:%M:%S')} UTC\n"
            f"Operating System: {platform.system()} {platform.release()}\n"
            f"Shell: {shell}\n"
            f"Working Directory: {working_dir}\n"
            f"Platform: {platform.platform()}"
        )