"""Error Classification System inspired by Claude Code.

Equivalente ao classifyAPIError() do Claude Code em services/api/errors.py.
Classifica erros em categorias padronizadas para analytics e retry decisions.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ErrorSeverity(str, Enum):
    """Níveis de severidade para erros.

    Usado para alertas, escalonamento e priorização de correções.
    """
    WARNING = "warning"      # Erros transitórios que podem se auto-corriger
    ERROR = "error"          # Erros que requerem intervenção mas não são críticos
    CRITICAL = "critical"    # Erros críticos que impedem operação


class ErrorCategory(str, Enum):
    """Categorias de erro padronizadas.

    Inspirado nas 15+ categorias do Claude Code:
    - aborted, api_timeout, repeated_529, capacity_off_switch
    - rate_limit, server_overload, prompt_too_long, pdf_too_large
    - tool_use_mismatch, unexpected_tool_result, duplicate_tool_use_id
    - invalid_model, credit_balance_low, invalid_api_key, auth_error
    """
    ABORTED = "aborted"
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"
    RATE_LIMIT = "rate_limit"
    SERVER_OVERLOAD = "server_overload"
    AUTH_ERROR = "auth_error"
    AUTH_TRANSIENT = "auth_transient"        # Autenticação transitória (pode funcionar no retry)
    NETWORK_ERROR = "network_error"
    TOOL_ERROR = "tool_error"                # Erros de execução de ferramentas
    VALIDATION_ERROR = "validation_error"
    CAPACITY_ERROR = "capacity_error"
    CAPACITY = "capacity"                    # Sem capacidade (529, overload)
    MEMORY_ERROR = "memory_error"            # Erros de memória/heap
    CONTEXT_OVERFLOW = "context_overflow"    # Contexto excedeu limite de tokens
    UNKNOWN = "unknown"


@dataclass
class ErrorClassification:
    """Resultado da classificação de um erro.

    Inclui categoria, severidade, retryability e metadados úteis
    para analytics e decisões de fallback.
    """
    category: ErrorCategory
    severity: ErrorSeverity
    retryable: bool
    fallback_available: bool = False
    status_code: int | None = None
    error_message: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário para logging/serialização."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "retryable": self.retryable,
            "fallback_available": self.fallback_available,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "context": self.context,
        }


def classify_error(error: Exception) -> ErrorCategory:
    """Classifica erro para analytics e retry decisions.

    Equivalente ao classifyAPIError() do Claude Code.

    Args:
        error: Exceção a ser classificada

    Returns:
        ErrorCategory correspondente
    """
    # Cancelled/Aborted
    if isinstance(error, asyncio.CancelledError):
        return ErrorCategory.ABORTED

    # Timeout
    if isinstance(error, TimeoutError):
        return ErrorCategory.TIMEOUT

    # Circuit breaker open
    try:
        from mindflow_backend.infra.resilience.circuit_breaker.core import CircuitOpenError
        if isinstance(error, CircuitOpenError):
            return ErrorCategory.CIRCUIT_OPEN
    except ImportError:
        pass

    # Network errors
    try:
        from mindflow_backend.exceptions.base.core_new import NetworkError
        if isinstance(error, NetworkError):
            return ErrorCategory.NETWORK_ERROR
    except ImportError:
        pass

    # Memory errors
    if isinstance(error, MemoryError):
        return ErrorCategory.MEMORY_ERROR

    # Check HTTP status codes if available
    status = getattr(error, 'status', None) or getattr(error, 'status_code', None)
    if status is not None:
        return _classify_by_status(status, error)

    # Check error message patterns
    msg = str(error).lower()
    if 'timeout' in msg:
        return ErrorCategory.TIMEOUT
    if 'rate limit' in msg or '429' in msg:
        return ErrorCategory.RATE_LIMIT
    if 'overload' in msg or '529' in msg:
        return ErrorCategory.SERVER_OVERLOAD
    if 'capacity' in msg:
        return ErrorCategory.CAPACITY
    if 'auth' in msg or '401' in msg or '403' in msg:
        return ErrorCategory.AUTH_ERROR
    if 'context' in msg and ('overflow' in msg or 'too long' in msg or 'maximum' in msg):
        return ErrorCategory.CONTEXT_OVERFLOW
    if 'memory' in msg or 'heap' in msg:
        return ErrorCategory.MEMORY_ERROR
    if 'tool' in msg and ('error' in msg or 'failed' in msg):
        return ErrorCategory.TOOL_ERROR

    return ErrorCategory.UNKNOWN


def classify_error_full(error: Exception) -> ErrorClassification:
    """Classificação completa de erro com severidade e retryability.

    Versão expandida que retorna ErrorClassification com todos os metadados.

    Args:
        error: Exceção a ser classificada

    Returns:
        ErrorClassification com categoria, severidade, retryability e contexto
    """
    category = classify_error(error)
    status = getattr(error, 'status', None) or getattr(error, 'status_code', None)

    # Determinar severidade
    severity = _determine_severity(category, error)

    # Determinar retryability
    retryable = category in {
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.SERVER_OVERLOAD,
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.CAPACITY,
        ErrorCategory.CAPACITY_ERROR,
        ErrorCategory.AUTH_TRANSIENT,
    }

    # Determinar fallback availability
    fallback_available = category in {
        ErrorCategory.CAPACITY,
        ErrorCategory.SERVER_OVERLOAD,
        ErrorCategory.CIRCUIT_OPEN,
    }

    return ErrorClassification(
        category=category,
        severity=severity,
        retryable=retryable,
        fallback_available=fallback_available,
        status_code=status,
        error_message=str(error),
    )


def _determine_severity(category: ErrorCategory, error: Exception) -> ErrorSeverity:
    """Determina severidade baseada na categoria do erro."""
    warning_categories = {
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.AUTH_TRANSIENT,
    }
    critical_categories = {
        ErrorCategory.CIRCUIT_OPEN,
        ErrorCategory.MEMORY_ERROR,
        ErrorCategory.CONTEXT_OVERFLOW,
    }

    if category in critical_categories:
        return ErrorSeverity.CRITICAL
    if category in warning_categories:
        return ErrorSeverity.WARNING
    if category in {ErrorCategory.SERVER_OVERLOAD, ErrorCategory.CAPACITY}:
        return ErrorSeverity.ERROR
    return ErrorSeverity.ERROR


def _classify_by_status(status: int, error: Exception) -> ErrorCategory:
    """Classifica erro por HTTP status code."""
    if status == 429:
        return ErrorCategory.RATE_LIMIT
    if status == 529:
        return ErrorCategory.SERVER_OVERLOAD
    if status in (401, 403):
        # Verificar se é transitório (pode funcionar em retry)
        msg = str(error).lower()
        if 'temporary' in msg or 'transient' in msg or 'retry' in msg:
            return ErrorCategory.AUTH_TRANSIENT
        return ErrorCategory.AUTH_ERROR
    if status in (500, 502, 503, 504):
        return ErrorCategory.SERVER_OVERLOAD
    if status == 408:
        return ErrorCategory.TIMEOUT
    if status == 413:
        return ErrorCategory.CONTEXT_OVERFLOW
    return ErrorCategory.UNKNOWN


def is_retryable(error: Exception) -> bool:
    """Verifica se o erro é retryable.

    Similar ao shouldRetry() do Claude Code.
    """
    category = classify_error(error)
    return category in {
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.SERVER_OVERLOAD,
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.CAPACITY,
        ErrorCategory.CAPACITY_ERROR,
        ErrorCategory.AUTH_TRANSIENT,
    }


def get_error_severity(error: Exception) -> ErrorSeverity:
    """Retorna severidade de um erro."""
    classification = classify_error_full(error)
    return classification.severity
