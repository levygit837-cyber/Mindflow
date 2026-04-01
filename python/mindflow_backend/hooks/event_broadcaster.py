"""HookEventBroadcaster — Sistema de broadcast de eventos de hook.

Emite eventos para UI e transcript persistence.
Equivalente de hookEvents.ts do Claude Code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable
import uuid

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HookExecutionState(StrEnum):
    """Estado de execução de um hook."""
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"


@dataclass
class HookExecutionEvent:
    """Evento de execução de hook — emitido para UI/transcript."""
    state: HookExecutionState
    hook_id: str
    hook_name: str
    hook_event: str
    stdout: str | None = None
    stderr: str | None = None
    output: str | None = None
    exit_code: int | None = None
    outcome: str | None = None


class HookEventBroadcaster:
    """Singleton que emite eventos de execução de hooks.

    Handlers podem registrar para receber eventos e decidir
    o que fazer (ex: converter para SDK messages, log, UI update).
    """

    _instance: HookEventBroadcaster | None = None

    def __init__(self) -> None:
        self._handlers: list[Callable[[HookExecutionEvent], Awaitable[None]]] = []
        self._pending_events: list[HookExecutionEvent] = []
        self._all_events_enabled = False

    @classmethod
    def get_instance(cls) -> HookEventBroadcaster:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, handler: Callable[[HookExecutionEvent], Awaitable[None]]) -> None:
        """Registra um handler para receber eventos."""
        self._handlers.append(handler)

    def enable_all_events(self) -> None:
        """Habilita emissão de todos os eventos (não apenas lifecycle)."""
        self._all_events_enabled = True

    async def emit(self, event: HookExecutionEvent) -> None:
        """Emite um evento para todos os handlers registrados."""
        if not self._handlers:
            self._pending_events.append(event)
            return

        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as exc:
                _logger.warning(
                    "hook_event_handler_error",
                    handler=str(handler),
                    error=str(exc),
                )

    def drain_pending(self) -> list[HookExecutionEvent]:
        """Retorna e limpa eventos pendentes."""
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events