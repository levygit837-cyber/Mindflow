"""Streaming Watchdog inspired by Claude Code.

Detecta streams travados e aborta com timeout.
Equivalente ao watchdog do Claude Code em StreamingToolExecutor.

Características:
- Monitora atividade do stream
- Auto-aborta após timeout
- Reset manual após atividade
- Thread-safe
"""

from __future__ import annotations

import time
import asyncio
from typing import Callable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class StreamingWatchdog:
    """Watchdog para detectar streams travados.

    Equivalente ao watchdog do Claude Code em StreamingToolExecutor.ts.

    Usage:
        watchdog = StreamingWatchdog(timeout=30.0)

        # Durante streaming
        watchdog.reset()  # Após cada chunk recebido

        if not watchdog.check():
            # Stream travado, abortar
            abort_stream()
    """

    def __init__(
        self,
        timeout: float = 30.0,
        on_timeout: Callable[[], None] | None = None,
    ):
        """Inicializa watchdog.

        Args:
            timeout: Timeout em segundos para detectar stream travado
            on_timeout: Callback opcional quando timeout ocorre
        """
        self.timeout = timeout
        self._last_activity = time.monotonic()
        self._aborted = False
        self._on_timeout = on_timeout

    def reset(self) -> None:
        """Reseta watchdog após atividade."""
        self._last_activity = time.monotonic()
        self._aborted = False

    def check(self) -> bool:
        """Verifica se stream está saudável.

        Returns:
            True se stream está saudável, False se travado/abortado
        """
        if self._aborted:
            return False

        elapsed = time.monotonic() - self._last_activity
        if elapsed >= self.timeout:
            _logger.warning(
                "stream_watchdog_timeout",
                elapsed=elapsed,
                timeout=self.timeout,
            )
            self._aborted = True
            if self._on_timeout:
                self._on_timeout()
            return False

        return True

    def abort(self) -> None:
        """Marca stream como abortado."""
        self._aborted = True
        _logger.info("stream_watchdog_aborted")

    @property
    def is_aborted(self) -> bool:
        """Verifica se stream foi abortado."""
        return self._aborted

    @property
    def elapsed_since_activity(self) -> float:
        """Retorna tempo desde última atividade em segundos."""
        return time.monotonic() - self._last_activity
