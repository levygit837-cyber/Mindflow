"""Persistent Retry Mode inspired by Claude Code.

Implementa retries longos para erros de capacidade (529), similar ao
persistent retry do Claude Code em withRetry.ts.

Características:
- Suporta retries de até 6 horas
- Chunked sleep para evitar idle detection
- Consecutive 529 tracking
- Reset cap para evitar retries infinitos
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from pydantic import BaseModel

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PersistentRetryConfig(BaseModel):
    """Configuração para retries persistentes."""
    enabled: bool = False
    max_persistent_retries: int = 100
    max_backoff_ms: int = 3_600_000  # 1 hora
    reset_cap_ms: int = 21_600_000  # 6 horas
    consecutive_529_threshold: int = 3
    chunk_sleep_ms: int = 60_000  # Chunk de 1 minuto


async def persistent_retry(
    operation: Callable[[], Any],
    config: PersistentRetryConfig | None = None,
    signal: asyncio.Event | None = None,
) -> Any:
    """Executa operação com persistent retry para erros de capacidade.

    Similar ao persistent retry do Claude Code.

    Args:
        operation: Função async a ser executada
        config: Configuração de persistent retry
        signal: Event para cancelamento

    Returns:
        Resultado da operação
    """
    cfg = config or PersistentRetryConfig()
    consecutive_529 = 0
    persistent_attempt = 0
    last_error: Exception | None = None

    while True:
        if signal and signal.is_set():
            raise asyncio.CancelledError("Persistent retry cancelled")

        try:
            return await operation()
        except Exception as error:
            last_error = error

            status = getattr(error, "status", None)
            if status == 529:
                consecutive_529 += 1
            else:
                consecutive_529 = 0

            if consecutive_529 < cfg.consecutive_529_threshold:
                raise

            persistent_attempt += 1
            if persistent_attempt > cfg.max_persistent_retries:
                raise

            delay_ms = min(
                cfg.max_backoff_ms * (2 ** (persistent_attempt - 1)),
                cfg.reset_cap_ms,
            )

            _logger.info(
                "persistent_retry",
                attempt=persistent_attempt,
                delay_ms=delay_ms,
                consecutive_529=consecutive_529,
            )

            remaining = delay_ms
            while remaining > 0:
                if signal and signal.is_set():
                    raise asyncio.CancelledError("Persistent retry cancelled")
                chunk = min(remaining, cfg.chunk_sleep_ms)
                await asyncio.sleep(chunk / 1000)
                remaining -= chunk
