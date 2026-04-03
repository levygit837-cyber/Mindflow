"""Hook timeout configuration and combined abort signal.

Inspirado em createCombinedAbortSignal() do Claude Code (utils/hooks.ts).
Gerencia timeouts configuráveis por hook e por evento.
"""

from __future__ import annotations

import asyncio
from typing import Any

# Default timeouts (seconds)
DEFAULT_HOOK_TIMEOUT = 30.0
TOOL_HOOK_TIMEOUT = 60.0  # PreToolUse/PostToolUse/PostToolUseFailure
SESSION_HOOK_TIMEOUT = 30.0  # SessionStart/SessionEnd/Stop
COMPACT_HOOK_TIMEOUT = 30.0  # PreCompact/PostCompact


class TimeoutConfig:
    """Configuração de timeout para hooks.

    Equivalente da lógica de timeout em executeHooks() do Claude Code.
    """

    @staticmethod
    def get_timeout(
        event: str,
        hook_timeout: float | None = None,
    ) -> float:
        """Retorna timeout efetivo para um hook.

        Precedência:
        1. hook_timeout (configurado no hook individual)
        2. event-specific timeout (por tipo de evento)
        3. DEFAULT_HOOK_TIMEOUT (fallback global)

        Args:
            event: Nome do evento (PreToolUse, PostToolUse, etc.)
            hook_timeout: Timeout configurado no hook (opcional)

        Returns:
            Timeout em segundos

        Examples:
            >>> TimeoutConfig.get_timeout("PreToolUse", None)
            60.0
            >>> TimeoutConfig.get_timeout("PreToolUse", 10.0)
            10.0
            >>> TimeoutConfig.get_timeout("SessionStart", None)
            30.0
        """
        if hook_timeout is not None:
            return hook_timeout

        # Event-specific timeouts
        if event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            return TOOL_HOOK_TIMEOUT

        if event in ("SessionStart", "SessionEnd", "Stop", "StopFailure"):
            return SESSION_HOOK_TIMEOUT

        if event in ("PreCompact", "PostCompact"):
            return COMPACT_HOOK_TIMEOUT

        return DEFAULT_HOOK_TIMEOUT

    @staticmethod
    async def create_timeout_task(
        timeout: float,
        abort_event: asyncio.Event,
    ) -> None:
        """Cria task que seta abort_event após timeout.

        Args:
            timeout: Timeout em segundos
            abort_event: Event que será setado ao expirar
        """
        try:
            await asyncio.sleep(timeout)
            abort_event.set()
        except asyncio.CancelledError:
            # Task foi cancelada (hook completou antes do timeout)
            pass

    @staticmethod
    def create_combined_abort_signal(
        manual_signal: asyncio.Event | None,
        timeout: float,
    ) -> tuple[asyncio.Event, asyncio.Task[Any]]:
        """Cria abort signal combinado (timeout + manual cancel).

        Equivalente de createCombinedAbortSignal() do Claude Code.

        Args:
            manual_signal: Event manual para cancelamento
            timeout: Timeout em segundos

        Returns:
            Tupla (abort_event, timeout_task)
            - abort_event: Event que será setado por timeout ou manual
            - timeout_task: Task do timeout (deve ser cancelada após uso)

        Examples:
            >>> abort_event, task = TimeoutConfig.create_combined_abort_signal(None, 30.0)
            >>> # Use abort_event.is_set() para verificar se abortou
            >>> task.cancel()  # Cleanup após uso
        """
        abort_event = asyncio.Event()

        # Se manual_signal já está set, aborta imediatamente
        if manual_signal and manual_signal.is_set():
            abort_event.set()

        # Cria task de timeout
        timeout_task = asyncio.create_task(
            TimeoutConfig.create_timeout_task(timeout, abort_event)
        )

        return abort_event, timeout_task


class AbortController:
    """Controller para gerenciar abort signals hierárquicos.

    Inspirado em AbortController do Claude Code.
    Permite criar abort signals que propagam de pai para filho.
    """

    def __init__(self, parent: AbortController | None = None) -> None:
        """Inicializa AbortController.

        Args:
            parent: Controller pai (opcional) - se pai abortar, filho também aborta
        """
        self._abort_event = asyncio.Event()
        self._parent = parent
        self._children: list[AbortController] = []

        if parent:
            parent._children.append(self)

    @property
    def signal(self) -> asyncio.Event:
        """Retorna abort signal (Event)."""
        return self._abort_event

    def abort(self) -> None:
        """Aborta este controller e todos os filhos."""
        self._abort_event.set()

        # Propaga para filhos
        for child in self._children:
            child.abort()

    def is_aborted(self) -> bool:
        """Verifica se foi abortado (este ou pai)."""
        if self._abort_event.is_set():
            return True

        if self._parent and self._parent.is_aborted():
            return True

        return False

    def check_or_raise(self) -> None:
        """Verifica se foi abortado e levanta exceção.

        Raises:
            asyncio.CancelledError: Se foi abortado
        """
        if self.is_aborted():
            raise asyncio.CancelledError("Operation aborted")
