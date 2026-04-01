"""InstructionsLoaded Handler — Executado quando um arquivo MIND.md é carregado.

Equivalent to Claude Code's InstructionsLoaded hook event.
Fired for each MIND.md file found during session start or memory reload.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookResult


class InstructionsLoadedHandler:
    """Handler para hooks InstructionsLoaded.

    Disparado para cada arquivo MIND.md carregado:
    - user: ~/.mindflow/MIND.md
    - project: ./.mindflow/MIND.md ou ./MIND.md
    - local: ./.mindflow/MIND.local.md ou ./MIND.local.md
    - managed: ~/.mindflow/managed/MIND.md

    O hook permite:
    - Validar conteúdo antes de injetar no prompt
    - Transformar ou filtrar instruções
    - Logar quais memórias foram carregadas
    - Bloquear carregamento de memórias específicas (via behavior=block)
    """

    @staticmethod
    async def execute(
        session_id: str,
        memory_type: str,
        file_path: str,
        content: str,
        *,
        cwd: str | None = None,
        timeout: float = 10.0,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks InstructionsLoaded para um arquivo MIND.md.

        Args:
            session_id: ID da sessão atual.
            memory_type: Tipo de memória (user, project, local, managed).
            file_path: Caminho do arquivo MIND.md carregado.
            content: Conteúdo do arquivo.
            cwd: Diretório de trabalho atual.
            timeout: Timeout em segundos para cada hook.
        """
        manager = HookManager.get_instance()
        async for result in manager.execute_instructions_loaded(
            session_id=session_id,
            memory_type=memory_type,
            file_path=file_path,
            content=content,
            cwd=cwd,
            timeout=timeout,
        ):
            yield result