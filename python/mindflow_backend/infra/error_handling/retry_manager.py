"""Granular Retry Manager inspired by Claude Code.

Equivalente ao withRetry.ts do Claude Code.
Implementa retry condicional por QuerySource (foreground vs background),
exponential backoff com jitter, e Retry-After header support.
"""

from __future__ import annotations

import asyncio
import random
import time
from enum import Enum
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

T = TypeVar("T")


class QuerySource(str, Enum):
    """Fontes de query para retry condicional.

    Foreground sources (usuário esperando) fazem retry em erros de capacidade.
    Background sources (títulos, summaries, sugestões) não fazem retry.
    """
    REPL_MAIN_THREAD = "repl_main_thread"
    AGENT_DEFAULT = "agent:default"
    AGENT_BUILTIN = "agent:builtin"
    COMPACT = "compact"
    HOOK_AGENT = "hook_agent"
    BACKGROUND = "background"


FOREGROUND_RETRY_SOURCES: set[QuerySource] = {
    QuerySource.REPL_MAIN_THREAD,
    QuerySource.AGENT_DEFAULT,
    QuerySource.AGENT_BUILTIN,
    QuerySource.COMPACT,
    QuerySource.HOOK_AGENT,
}

BASE_DELAY_MS = 500
MAX_DELAY_MS = 3600000  # 1 hora
MAX_529_RETRIES = 3


class RetryConfig(BaseModel):
    """Configuração de retry granular."""
    max_retries: int = 10
    backoff_base: float = 0.5
    backoff_max: float = 3600.0
    jitter: bool = True
    retry_on_status: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504, 529]
    )
    retry_sources: set[QuerySource] = Field(
        default_factory=lambda: FOREGROUND_RETRY_SOURCES
    )
    respect_retry_after: bool = True


def get_retry_delay(
    attempt: int,
    retry_after: str | None = None,
    max_delay: float = MAX_DELAY_MS / 1000,
) -> float:
    """Calcula delay respeitando Retry-After header.

    Equivalente ao getRetryDelay() do Claude Code.

    Args:
        attempt: Número da tentativa atual
        retry_after: Valor do header Retry-After (segundos)
        max_delay: Delay máximo em segundos

    Returns:
        Delay em segundos
    """
    if retry_after:
        try:
            return float(retry_after)
        except (ValueError, TypeError):
            pass

    base = BASE_DELAY_MS / 1000
    delay = min(base * (2 ** attempt), max_delay)

    # Exponential backoff com jitter (como Claude Code)
    delay = delay * (0.5 + random.random())

    return delay


def should_retry_status(status: int, config: RetryConfig) -> bool:
    """Verifica se status code é retryable."""
    return status in config.retry_on_status


def is_foreground_source(source: QuerySource | None) -> bool:
    """Verifica se fonte é foreground (deve retry em capacity errors)."""
    if source is None:
        return True
    return source in FOREGROUND_RETRY_SOURCES


async def with_granular_retry(
    operation: Callable[[], Any],
    config: RetryConfig | None = None,
    source: QuerySource | None = None,
    signal: asyncio.Event | None = None,
) -> Any:
    """Executa operação com retry granular por fonte.

    Equivalente ao withRetry() do Claude Code.

    Args:
        operation: Função async a ser executada
        config: Configuração de retry
        source: Fonte da query (foreground/background)
        signal: Event para cancelamento

    Returns:
        Resultado da operação

    Raises:
        Exception: Se todas as tentativas falharem
    """
    cfg = config or RetryConfig()
    consecutive_529 = 0
    last_error: Exception | None = None

    for attempt in range(1, cfg.max_retries + 2):
        if signal and signal.is_set():
            raise asyncio.CancelledError("Retry cancelled")

        try:
            return await operation()
        except Exception as error:
            last_error = error

            from .classifier import classify_error, ErrorCategory, is_retryable

            category = classify_error(error)

            if not is_retryable(error):
                raise

            if attempt > cfg.max_retries:
                raise

            # Verificar 529 consecutivos
            status = getattr(error, "status", None)
            if status == 529:
                consecutive_529 += 1
                if consecutive_529 >= MAX_529_RETRIES:
                    if not is_foreground_source(source):
                        raise
            else:
                consecutive_529 = 0

            retry_after = getattr(error, "retry_after", None)
            delay = get_retry_delay(attempt - 1, retry_after)

            _logger.info(
                "retry_attempt",
                attempt=attempt,
                delay=delay,
                category=category.value,
                source=source.value if source else None,
            )

            await asyncio.sleep(delay)

    if last_error:
        raise last_error
