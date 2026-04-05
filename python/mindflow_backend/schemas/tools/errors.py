"""Synthetic Error Messages - Mensagens de erro contextuais.

Inspirado no sistema de erros do Claude Code.
Fornece mensagens de erro claras e contextuais para diferentes cenários.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from mindflow_backend.schemas.tools.result import ResultTruncation, ToolResult, TruncationReason


class ErrorReason(Enum):
    """Razões para erros sintéticos."""

    USER_INTERRUPTED = "user_interrupted"
    SIBLING_ERROR = "sibling_error"
    STREAMING_FALLBACK = "streaming_fallback"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    TOOL_NOT_FOUND = "tool_not_found"
    EXECUTION_ABORTED = "execution_aborted"
    INVALID_INPUT = "invalid_input"
    RESULT_TOO_LARGE = "result_too_large"


@dataclass
class SyntheticError:
    """Erro sintético com mensagem contextual.

    Attributes:
        reason: Razão do erro
        tool_id: ID da ferramenta
        tool_name: Nome da ferramenta
        original_error: Erro original (opcional)
        context: Contexto adicional (opcional)
    """

    reason: ErrorReason
    tool_id: str
    tool_name: str
    original_error: str | None = None
    context: dict[str, Any] | None = None

    @property
    def message(self) -> str:
        """Gera mensagem contextual baseada no motivo."""
        match self.reason:
            case ErrorReason.USER_INTERRUPTED:
                return f"❌ Operação cancelada pelo usuário em '{self.tool_name}'"

            case ErrorReason.SIBLING_ERROR:
                return (
                    f"⚠️ Execução abortada em '{self.tool_name}': "
                    f"ferramenta irmã '{self.context.get('failed_tool', 'unknown')}' "
                    f"falhou. Comandos dependentes foram cancelados."
                )

            case ErrorReason.STREAMING_FALLBACK:
                return (
                    f"🔄 Streaming fallback em '{self.tool_name}': "
                    f"execução descartada devido a retry da API."
                )

            case ErrorReason.TIMEOUT:
                timeout = self.context.get("timeout_seconds", 30) if self.context else 30
                timeout_str = f"{int(timeout)}s" if timeout == int(timeout) else f"{timeout}s"
                return (
                    f"⏱️ Timeout em '{self.tool_name}': excedeu o limite de "
                    f"{timeout_str} de execução."
                )

            case ErrorReason.PERMISSION_DENIED:
                reason = self.context.get("reason", "") if self.context else ""
                return (
                    f"🔒 Permissão negada para '{self.tool_name}': "
                    f"execução requer aprovação do usuário."
                    + (f" Motivo: {reason}" if reason else "")
                )

            case ErrorReason.TOOL_NOT_FOUND:
                return (
                    f"❓ Ferramenta não encontrada: '{self.tool_name}'. "
                    f"Verifique se a ferramenta está registrada."
                )

            case ErrorReason.EXECUTION_ABORTED:
                return (
                    f"🛑 Execução abortada em '{self.tool_name}': "
                    f"cancelada por erro em ferramenta dependente."
                )

            case ErrorReason.INVALID_INPUT:
                error = self.original_error or "Input inválido"
                return (
                    f"📝 Input inválido para '{self.tool_name}': {error}"
                )

            case ErrorReason.RESULT_TOO_LARGE:
                size = self.context.get("size", 0) if self.context else 0
                max_size = self.context.get("max_size", 100_000) if self.context else 100_000
                return (
                    f"📊 Resultado muito grande para '{self.tool_name}': "
                    f"{size:,} caracteres (máximo: {max_size:,})."
                )

            case _:
                return f"❌ Erro em '{self.tool_name}': {self.original_error or 'Erro desconhecido'}"

    def to_tool_result(self) -> ToolResult:
        """Converte para ToolResult com is_error=True.

        Returns:
            ToolResult com erro sintético
        """
        return ToolResult(
            data=self.message,
            success=False,
            error_message=self.message,
            truncation=ResultTruncation(
                was_truncated=False,
                reason=TruncationReason.SIZE_LIMIT,
            ),
            legacy_metadata={
                "error_reason": self.reason.value,
                "tool_id": self.tool_id,
                "tool_name": self.tool_name,
                "synthetic": True,
            },
        )


def create_user_interrupted_error(tool_id: str, tool_name: str) -> SyntheticError:
    """Cria erro de interrupção pelo usuário."""
    return SyntheticError(
        reason=ErrorReason.USER_INTERRUPTED,
        tool_id=tool_id,
        tool_name=tool_name,
    )


def create_sibling_error(
    tool_id: str,
    tool_name: str,
    failed_tool: str,
) -> SyntheticError:
    """Cria erro de falha em ferramenta irmã."""
    return SyntheticError(
        reason=ErrorReason.SIBLING_ERROR,
        tool_id=tool_id,
        tool_name=tool_name,
        context={"failed_tool": failed_tool},
    )


def create_streaming_fallback_error(tool_id: str, tool_name: str) -> SyntheticError:
    """Cria erro de streaming fallback."""
    return SyntheticError(
        reason=ErrorReason.STREAMING_FALLBACK,
        tool_id=tool_id,
        tool_name=tool_name,
    )


def create_timeout_error(
    tool_id: str,
    tool_name: str,
    timeout_seconds: float,
) -> SyntheticError:
    """Cria erro de timeout."""
    return SyntheticError(
        reason=ErrorReason.TIMEOUT,
        tool_id=tool_id,
        tool_name=tool_name,
        context={"timeout_seconds": timeout_seconds},
    )


def create_permission_denied_error(
    tool_id: str,
    tool_name: str,
    reason: str = "",
) -> SyntheticError:
    """Cria erro de permissão negada."""
    return SyntheticError(
        reason=ErrorReason.PERMISSION_DENIED,
        tool_id=tool_id,
        tool_name=tool_name,
        context={"reason": reason},
    )


def create_tool_not_found_error(tool_id: str, tool_name: str) -> SyntheticError:
    """Cria erro de ferramenta não encontrada."""
    return SyntheticError(
        reason=ErrorReason.TOOL_NOT_FOUND,
        tool_id=tool_id,
        tool_name=tool_name,
    )


def create_execution_aborted_error(tool_id: str, tool_name: str) -> SyntheticError:
    """Cria erro de execução abortada."""
    return SyntheticError(
        reason=ErrorReason.EXECUTION_ABORTED,
        tool_id=tool_id,
        tool_name=tool_name,
    )


def create_invalid_input_error(
    tool_id: str,
    tool_name: str,
    error: str,
) -> SyntheticError:
    """Cria erro de input inválido."""
    return SyntheticError(
        reason=ErrorReason.INVALID_INPUT,
        tool_id=tool_id,
        tool_name=tool_name,
        original_error=error,
    )


def create_result_too_large_error(
    tool_id: str,
    tool_name: str,
    size: int,
    max_size: int,
) -> SyntheticError:
    """Cria erro de resultado muito grande."""
    return SyntheticError(
        reason=ErrorReason.RESULT_TOO_LARGE,
        tool_id=tool_id,
        tool_name=tool_name,
        context={"size": size, "max_size": max_size},
    )