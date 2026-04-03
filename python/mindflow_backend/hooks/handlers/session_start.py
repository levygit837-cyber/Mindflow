"""SessionStart Handler — Executado ao iniciar sessão.

After executing standard SessionStart hooks, also loads all MIND.md memory files
and fires InstructionsLoaded hooks for each file found.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.plugins.manager import get_plugin_manager

logger = logging.getLogger(__name__)


class SessionStartHandler:
    """Handler para hooks SessionStart.

    Fluxo de execução:
    1. Executa hooks SessionStart registrados (comandos, plugins, etc.)
    2. Carrega todos os arquivos MIND.md (user, project, local, managed)
    3. Dispara InstructionsLoaded para cada arquivo encontrado
    """

    @staticmethod
    async def execute(
        session_id: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> AsyncGenerator[HookResult, None]:
        manager = HookManager.get_instance()
        plugin_manager = get_plugin_manager()

        await plugin_manager.activate_session(session_id, cwd=cwd)

        # 1. Execute standard SessionStart hooks
        async for result in manager.execute_session_start(
            session_id=session_id,
            cwd=cwd,
            timeout=timeout,
        ):
            yield result

        # 2. Load MIND.md memory files and fire InstructionsLoaded hooks
        async for result in SessionStartHandler._load_memory_files(
            session_id=session_id,
            cwd=cwd or os.getcwd(),
            timeout=timeout,
        ):
            yield result

    @staticmethod
    async def _load_memory_files(
        session_id: str,
        cwd: str,
        timeout: float = 10.0,
    ) -> AsyncGenerator[HookResult, None]:
        """Load all MIND.md files and fire InstructionsLoaded for each.

        Uses MemoryFileLoader to find all 4 memory types, then fires
        InstructionsLoaded hooks so other systems can react (logging, validation, etc.).
        """
        from mindflow_backend.agents.prompts.layers.memory_loader import MemoryFileLoader

        loader = MemoryFileLoader()
        memory_files = await loader.load_all(cwd)

        if not memory_files:
            logger.debug("No MIND.md memory files found in %s", cwd)
            return

        logger.info(
            "Loaded %d MIND.md memory files: %s",
            len(memory_files),
            [mf.source.value for mf in memory_files],
        )

        # Fire InstructionsLoaded hook for each file
        manager = HookManager.get_instance()
        for mf in memory_files:
            async for result in manager.execute_instructions_loaded(
                session_id=session_id,
                memory_type=mf.source.value,
                file_path=mf.path,
                content=mf.content,
                cwd=cwd,
                timeout=timeout,
            ):
                yield result
